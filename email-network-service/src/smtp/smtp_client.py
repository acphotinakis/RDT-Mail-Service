"""
Implements an SMTP client for sending emails.

This module provides `SMTPClient`, a class that handles the client-side
of the SMTP protocol. It uses the Reliable Data Transfer (RDT) protocol
over UDP to communicate with an SMTP server. The client is responsible for
the entire email sending transaction, from the initial handshake to sending
the email data and closing the connection.
"""

import socket
from typing import Tuple
from src.common.logger import *
from src.config import Config
from src.common.exceptions import SMTPProtocolError, SMTPConnectionError
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_dispatcher import RDTDispatcher

# SMTP Response Codes
SMTP_READY = 220
SMTP_OK = 250
SMTP_CLOSING = 221
SMTP_START_INPUT = 354


class SMTPClient:
    """
    An SMTP client that sends emails using the RDT protocol over UDP.

    This class encapsulates the entire SMTP workflow for sending an email. It
    manages a UDP socket, an RDT sender and receiver, and the sequence of SMTP
    commands required to complete an email transaction.

    The client binds to an ephemeral port, allowing multiple instances to run
    concurrently.

    Attributes:
        log: A logger instance for the class.
        sock (socket.socket): The UDP socket used for communication.
        dispatcher (RDTDispatcher): The dispatcher managing incoming RDT packets.
        rdt_sender (RDTSender): The RDT sender for reliable data transmission.
        rdt_receiver (RDTReceiver): The RDT receiver for reliable data reception.
        receiver_gen: A generator for receiving RDT packets.
        is_connected (bool): A flag indicating the connection state.
    """

    def __init__(self):
        """
        Initializes the SMTPClient.

        This sets up the UDP socket, binds it to an ephemeral port, and
        initializes the RDT dispatcher, sender, and receiver components.

        Side Effects:
            - Creates and binds a UDP socket.
            - Starts a background thread for the RDT dispatcher.
        """

        # 1. Socket Setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Use Port 0 (Ephemeral) so the OS assigns a random available port.
        # This allows multiple SMTPClient instances to run in parallel threads.
        self.sock.bind((Config.CLIENT_IP, 0))
        self.sock.settimeout(Config.RDT_TIMEOUT)

        # 2. RDT Setup
        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        self.rdt_sender = RDTSender(
            Config.SMTP_SERVER_HOST, Config.SMTP_SERVER_PORT, self.dispatcher
        )
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False

        log_info_detailed(
            f"SMTP Client initialized on {self.sock.getsockname()[0]}:{self.sock.getsockname()[1]}"
        )
        log_info_detailed(self.to_string())

    def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
        """
        Sends an email by executing the full SMTP transaction.

        Args:
            sender (str): The sender's email address.
            recipient (str): The recipient's email address.
            subject (str): The subject of the email.
            body (str): The body content of the email.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        with log_block_detailed("SMTPClient.send_email"):
            log_info_detailed(
                "Beginning SMTP transaction",
                extra={"sender": sender, "recipient": recipient, "subject": subject},
            )
            try:
                self._connect()
                self._do_handshake()
                self._send_mail_from(sender)
                self._send_rcpt_to(recipient)
                self._send_data(subject, body)
                self._send_quit()
                log_info_detailed("SMTP transaction completed successfully.")
                return True
            except Exception as e:
                log_error_detailed(f"Email transaction failed: {e}")
                if self.is_connected:
                    try:
                        self._send_command("QUIT")
                    except Exception:
                        log_warning_detailed("Failed to send QUIT during cleanup.", exc_info=True)
                return False
            finally:
                self._close()

    def _connect(self):
        """
        Establishes a connection to the SMTP server.

        Instead of sending an empty RDT packet (which is an implementation detail hack),
        this method sends a standard 'NOOP' command. This serves two purposes:
        1. It acts as a concrete Application Layer handshake, forcing the server to
           initialize the session and send the '220' Welcome banner.
        2. It ensures the first packet contains valid SMTP protocol data.

        Raises:
            SMTPConnectionError: If the server does not respond with the expected code.
        """
        with log_block_detailed("SMTPClient._connect"):
            log_debug_detailed("Resetting receiver generator for new session.")
            self.receiver_gen = self.rdt_receiver.start_receiving()

            # Send NOOP to initiate the session
            log_debug_detailed("Sending NOOP handshake command.")
            self._send_command("NOOP")

            # 1. Expect Welcome Message (220) from Session Creation
            try:
                code, msg = self._get_reply()
                log_debug_detailed(f"Handshake welcome reply: code={code}, msg={msg!r}")
                if code != SMTP_READY:
                    raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
            except Exception as e:
                raise SMTPConnectionError(f"Connection failed during handshake: {e}")

            # 2. Expect Response to NOOP (250)
            # We must consume this response so it doesn't interfere with the subsequent HELO.
            try:
                code_noop, msg_noop = self._get_reply()
                log_debug_detailed(f"NOOP command reply: code={code_noop}, msg={msg_noop!r}")
                if code_noop != SMTP_OK:
                    log_warning_detailed(f"Initial NOOP handshake returned code: {code_noop}")
            except Exception:
                # If the server is modified in the future to not send 250 for the
                # trigger packet, we ignore read errors here to remain robust.
                log_debug_detailed("NOOP response read skipped due to exception.", exc_info=True)

            self.is_connected = True
            log_info_detailed("SMTP connection established and session ready.")

    def _do_handshake(self):
        """
        Performs the SMTP `HELO` handshake.

        Raises:
            SMTPProtocolError: If the server does not respond with a `250 OK`.
        """
        with log_block_detailed("SMTPClient._do_handshake"):
            log_debug_detailed("Sending HELO command.")
            self._send_command("HELO localhost")
            code, msg = self._get_reply()
            log_debug_detailed(f"HELO reply: code={code}, msg={msg!r}")
            if code != SMTP_OK:
                raise SMTPProtocolError("HELO failed")

    def _send_mail_from(self, sender: str):
        """
        Sends the `MAIL FROM` command.
        """
        with log_block_detailed("SMTPClient._send_mail_from"):
            log_info_detailed(f"Issuing MAIL FROM for {sender}.")
            self._send_command(f"MAIL FROM:<{sender}>")
            code, msg = self._get_reply()
            log_debug_detailed(f"MAIL FROM reply: code={code}, msg={msg!r}")
            if code != SMTP_OK:
                raise SMTPProtocolError("MAIL FROM failed")

    def _send_rcpt_to(self, recipient: str):
        """
        Sends the `RCPT TO` command.
        """
        with log_block_detailed("SMTPClient._send_rcpt_to"):
            log_info_detailed(f"Issuing RCPT TO for {recipient}.")
            self._send_command(f"RCPT TO:<{recipient}>")
            code, msg = self._get_reply()
            log_debug_detailed(f"RCPT TO reply: code={code}, msg={msg!r}")
            if code != SMTP_OK:
                raise SMTPProtocolError("RCPT TO failed")

    def _send_data(self, subject: str, body: str):
        """
        Sends the `DATA` command and the email content.
        """
        with log_block_detailed("SMTPClient._send_data"):
            log_info_detailed("Issuing DATA command.")
            self._send_command("DATA")
            code, msg = self._get_reply()
            log_debug_detailed(f"DATA reply: code={code}, msg={msg!r}")
            if code != SMTP_START_INPUT:
                raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

            # --- CHUNKING LOGIC ---
            full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
            payload_bytes = full_payload.encode("ascii")
            total_len = len(payload_bytes)
            sent = 0

            log_debug_detailed(
                f"Streaming email payload: total_bytes={total_len}, "
                f"chunk_size={Config.MAX_PAYLOAD_SIZE}"
            )

            while sent < total_len:
                chunk = payload_bytes[sent : sent + Config.MAX_PAYLOAD_SIZE]
                log_debug_detailed(
                    f"Sending chunk bytes[{sent}:{sent + len(chunk)}] " f"({len(chunk)} bytes)."
                )
                self.rdt_sender.send(chunk)
                sent += len(chunk)

            code, msg = self._get_reply()
            log_debug_detailed(f"DATA finalization reply: code={code}, msg={msg!r}")
            if code != SMTP_OK:
                raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

    def _send_quit(self):
        """
        Sends the `QUIT` command to terminate the SMTP session.
        """
        with log_block_detailed("SMTPClient._send_quit"):
            log_info_detailed("Issuing QUIT command.")
            self._send_command("QUIT")
            try:
                code, msg = self._get_reply()
                log_debug_detailed(f"QUIT reply: code={code}, msg={msg!r}")
            except Exception:
                log_warning_detailed("No reply received for QUIT.", exc_info=True)
            # self.is_connected = False

    def _send_command(self, cmd: str):
        """
        Sends an SMTP command string to the server via the RDT sender.
        Appends CRLF as required by protocol.
        """
        log_debug_detailed(f"Sending command: {cmd}")
        self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

    def _get_reply(self) -> Tuple[int, str]:
        """
        Receives and parses a reply from the SMTP server.

        Returns:
            Tuple[int, str]: Status code and message.
        """
        try:
            data_bytes, addr = next(self.receiver_gen)
            reply = data_bytes.decode("ascii").strip()
            log_debug_detailed(f"Received reply from {addr}: {reply!r}")

            if len(reply) < 3:
                raise SMTPProtocolError(f"Malformed reply: {reply}")

            code = int(reply[:3])
            msg = reply[4:] if len(reply) > 4 else ""
            return code, msg
        except StopIteration:
            raise SMTPConnectionError("Connection closed")

    def _close(self):
        """
        Closes the socket and stops the RDT dispatcher thread.
        """
        with log_block_detailed("SMTPClient._close"):
            if self.dispatcher:
                log_debug_detailed("Stopping dispatcher.")
                self.dispatcher.stop()
            if self.sock:
                addr = self.sock.getsockname()
                log_debug_detailed(f"Closing socket bound to {addr}.")
                self.sock.close()

    def to_string(self) -> str:
        """
        Returns a detailed diagnostic overview of the SMTPClient state,
        including socket info, dispatcher status, RDT components, and
        connection flags.
        """
        sock = self.sock
        dispatcher_thread = self.dispatcher._thread if self.dispatcher else None

        props = {
            "Socket Bound": f"{sock.getsockname()[0]}:{sock.getsockname()[1]}",
            "Server Target": f"{Config.SMTP_SERVER_HOST}:{Config.SMTP_SERVER_PORT}",
            "RDT Timeout": Config.RDT_TIMEOUT,
            "Max Payload Size": Config.MAX_PAYLOAD_SIZE,
            # --- Connection State ---
            "Connected": self.is_connected,
            # --- Dispatcher ---
            "Dispatcher Running": self.dispatcher.running,
            "Dispatcher Thread Alive": (
                dispatcher_thread.is_alive() if dispatcher_thread else False
            ),
            "Dispatcher Thread Name": (dispatcher_thread.name if dispatcher_thread else None),
            # --- RDT Components ---
            "RDT Sender Dest": f"{self.rdt_sender.dest_addr}",
            "Receiver Active": self.rdt_receiver.running,
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nSMTPClient State:"]
        lines.append("-" * (longest + 30))

        for key, value in props.items():
            lines.append(f"{key.ljust(longest)} : {value}")

        lines.append("-" * (longest + 30))

        return "\n".join(lines)
