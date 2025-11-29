import time
from typing import Optional
from common.logger import get_class_logger
from common.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    CLIENT_IP,
    CLIENT_LISTENING_PORT,
)
from common.exceptions import SMTPProtocolError, SMTPConnectionError
from rdt.rdt_sender import RDTSender
from rdt.rdt_receiver import RDTReceiver


# SMTP Response Codes
SMTP_READY = 220
SMTP_OK = 250
SMTP_CLOSING = 221
SMTP_START_INPUT = 354
SMTP_SYNTAX_ERROR = 500
SMTP_COMMAND_NOT_IMPLEMENTED = 502
SMTP_BAD_SEQUENCE = 503


class SMTPClient:
    """
    An SMTP client that sends emails using a custom RDT transport layer.
    """

    def __init__(self):
        """
        Initializes the SMTP client components.
        """
        self.log = get_class_logger(self)

        # RDT Sender to transmit commands to the server
        self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT)

        # RDT Receiver to listen for replies from the server.
        # Note: The network architecture must ensure server replies are
        # routed to this listening port.
        self.rdt_receiver = RDTReceiver(CLIENT_IP, CLIENT_LISTENING_PORT)

        self.receiver_gen = None
        self.is_connected = False
        self.log.info("SMTPClient initialized.")

    def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
        """
        Executes the full SMTP protocol sequence to send an email.

        Args:
            sender: The email address of the sender.
            recipient: The email address of the recipient.
            subject: The subject line of the email.
            body: The main content of the email.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        self.log.info(f"Starting email transaction to {recipient}...")
        try:
            self._connect()
            self._do_handshake()
            self._send_mail_from(sender)
            self._send_rcpt_to(recipient)
            self._send_data(subject, body)
            self._send_quit()
            self.log.info("Email transaction completed successfully.")
            return True

        except (SMTPProtocolError, SMTPConnectionError, Exception) as e:
            self.log.error(f"Email transaction failed: {e}")
            # Try to send QUIT to close nicely if connection is still considered open
            if self.is_connected:
                try:
                    self._send_command("QUIT")
                except:
                    pass
            return False
        finally:
            self._close()

    # --- Protocol Steps ---

    def _connect(self):
        """Starts the RDT receiver and waits for the server's greeting."""
        self.log.debug("Starting RDT receiver and waiting for connection...")
        try:
            # Start listening for server responses
            self.receiver_gen = self.rdt_receiver.start_receiving()

            # Wait for 220 Service ready greeting
            code, msg = self._get_reply()
            if code != SMTP_READY:
                raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")

            self.is_connected = True
            self.log.info(f"Connected to SMTP Server: {msg}")

        except Exception as e:
            self.log.error(f"Failed to connect to SMTP server: {e}")
            raise SMTPConnectionError(f"Connection failed: {e}")

    def _do_handshake(self):
        """Sends HELO command and identifies the client."""
        # Using 'localhost' as domain for simplicity in this project context
        self._send_command("HELO localhost")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"HELO failed. Got: {code} {msg}")

    def _send_mail_from(self, sender: str):
        """Sends MAIL FROM command to specify the sender."""
        self._send_command(f"MAIL FROM:<{sender}>")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"MAIL FROM failed. Got: {code} {msg}")

    def _send_rcpt_to(self, recipient: str):
        """Sends RCPT TO command to specify the recipient."""
        self._send_command(f"RCPT TO:<{recipient}>")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"RCPT TO failed. Got: {code} {msg}")

    def _send_data(self, subject: str, body: str):
        """Sends DATA command followed by the email content."""
        self._send_command("DATA")
        code, msg = self._get_reply()
        if code != SMTP_START_INPUT:
            raise SMTPProtocolError(f"DATA command not accepted. Got: {code} {msg}")

        # Construct the full email payload with headers
        email_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"

        self.log.debug(f"Sending email payload ({len(email_payload)} bytes).")
        # Send the payload directly via RDT sender without appending another \r\n
        self.rdt_sender.send(email_payload.encode("ascii"))

        # Wait for final confirmation after sending data
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"Data transmission failed. Got: {code} {msg}")

    def _send_quit(self):
        """Sends QUIT command to close the session nicely."""
        self._send_command("QUIT")
        # We expect a 221 closing connection reply, but we don't strictly need to enforce it
        # before closing our end.
        try:
            code, msg = self._get_reply()
            self.log.debug(f"Server quit response: {code} {msg}")
        except Exception:
            self.log.debug("Did not receive final QUIT response, closing anyway.")
        self.is_connected = False

    # --- Helper Methods ---

    def _send_command(self, cmd: str):
        """Encodes and sends an SMTP command ending with CRLF via RDT."""
        full_cmd = cmd + "\r\n"
        self.log.debug(f">>> {cmd}")
        self.rdt_sender.send(full_cmd.encode("ascii"))

    def _get_reply(self) -> tuple[int, str]:
        """
        Receives a reply from the server via RDT.
        Returns parsed (error_code, message_string).
        """
        self.log.debug("Waiting for response...")
        try:
            # Get next data chunk from the receiver generator
            data_bytes = next(self.receiver_gen)
            reply_str = data_bytes.decode("ascii").strip()
            self.log.debug(f"<<< {reply_str}")

            # Parse out the 3-digit code and the message
            if len(reply_str) < 3 or not reply_str[:3].isdigit():
                raise SMTPProtocolError(f"Malformed server reply: {reply_str}")

            code = int(reply_str[:3])
            msg = reply_str[4:] if len(reply_str) > 4 else ""
            return code, msg

        except StopIteration:
            self.log.error("Connection closed unexpectedly by server.")
            raise SMTPConnectionError("Server closed connection unexpectedly.")
        except UnicodeDecodeError:
            self.log.error("Received non-ASCII data from server.")
            raise SMTPProtocolError("Received invalid data from server.")
        except Exception as e:
            self.log.error(f"Error receiving reply: {e}")
            raise e

    def _close(self):
        """Cleans up RDT resources."""
        self.log.debug("Closing RDT resources.")
        if self.rdt_receiver:
            self.rdt_receiver.stop()
        if self.rdt_sender:
            self.rdt_sender.close()
        self.is_connected = False
