import time
import socket
from typing import Optional
from src.common.logger import get_class_logger
from src.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    CLIENT_IP,
    CLIENT_LISTENING_PORT,
    RDT_TIMEOUT,
)
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
    An SMTP client that uses the RDTDispatcher to multiplex a single socket
    for both sending and receiving.
    """

    def __init__(self):
        self.log = get_class_logger(self)

        # 1. Create and Bind Shared Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow reuse address to avoid "Address already in use" during rapid testing
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((CLIENT_IP, CLIENT_LISTENING_PORT))
        self.sock.settimeout(RDT_TIMEOUT)

        # 2. Init Dispatcher
        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        # 3. Init Sender & Receiver
        self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)

        # yield_addr=False because we know who we are talking to (the server)
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher, yield_addr=False)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False
        self.log.info("SMTPClient initialized with RDTDispatcher.")

    def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
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

        except (SMTPProtocolError, SMTPConnectionError) as e:
            self.log.error(f"Email transaction failed: {e}")
            if self.is_connected:
                try:
                    self._send_command("QUIT")
                except:
                    pass
            return False
        except ConnectionError:
            self.log.error("Fatal RDT connection error (max retries reached).")
            return False
        except Exception as e:
            self.log.exception(f"Unexpected error: {e}")
            return False
        finally:
            self._close()

    def _connect(self):
        self.log.debug("Connecting to SMTP Server...")
        try:
            # Re-initialize generator to ensure clean state
            self.receiver_gen = self.rdt_receiver.start_receiving()

            # Send empty packet to trigger server 220 welcome
            self.rdt_sender.send(b"")

            code, msg = self._get_reply()
            if code != SMTP_READY:
                raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")

            self.is_connected = True
            self.log.info(f"Connected: {msg}")

        except Exception as e:
            raise SMTPConnectionError(f"Connection failed: {e}")

    def _do_handshake(self):
        self._send_command("HELO localhost")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"HELO failed. Got: {code} {msg}")

    def _send_mail_from(self, sender: str):
        self._send_command(f"MAIL FROM:<{sender}>")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"MAIL FROM failed. Got: {code} {msg}")

    def _send_rcpt_to(self, recipient: str):
        self._send_command(f"RCPT TO:<{recipient}>")
        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"RCPT TO failed. Got: {code} {msg}")

    def _send_data(self, subject: str, body: str):
        self._send_command("DATA")
        code, msg = self._get_reply()
        if code != SMTP_START_INPUT:
            raise SMTPProtocolError(f"DATA command not accepted. Got: {code} {msg}")

        email_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
        self.log.debug(f"Sending email payload ({len(email_payload)} bytes).")
        self.rdt_sender.send(email_payload.encode("ascii"))

        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"Data transmission failed. Got: {code} {msg}")

    def _send_quit(self):
        self._send_command("QUIT")
        try:
            code, msg = self._get_reply()
            self.log.debug(f"Server quit response: {code} {msg}")
        except Exception:
            pass
        self.is_connected = False

    def _send_command(self, cmd: str):
        full_cmd = cmd + "\r\n"
        self.log.debug(f">>> {cmd}")
        self.rdt_sender.send(full_cmd.encode("ascii"))

    def _get_reply(self) -> tuple[int, str]:
        self.log.debug("Waiting for response...")
        try:
            # This now pulls from the Dispatcher Queue via the generator
            packet = next(self.receiver_gen)

            if isinstance(packet, tuple):
                data_bytes, _ = packet
            else:
                data_bytes = packet

            reply_str = data_bytes.decode("ascii").strip()
            self.log.debug(f"<<< {reply_str}")

            if len(reply_str) < 3 or not reply_str[:3].isdigit():
                raise SMTPProtocolError(f"Malformed server reply: {reply_str}")

            code = int(reply_str[:3])
            msg = reply_str[4:] if len(reply_str) > 4 else ""
            return code, msg

        except StopIteration:
            raise SMTPConnectionError("Server closed connection unexpectedly.")
        except Exception as e:
            raise e

    def _close(self):
        self.log.debug("Closing SMTP Client.")
        if self.dispatcher:
            self.dispatcher.stop()

        # Dispatcher does not close socket automatically to allow reuse logic if needed,
        # but here we own the socket.
        if self.sock:
            self.sock.close()

        self.is_connected = False
