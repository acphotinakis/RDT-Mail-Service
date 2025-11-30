import socket
from typing import Optional, Tuple
from src.common.logger import get_class_logger
from src.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    CLIENT_IP,
    RDT_TIMEOUT,
)
from src.rdt.rdt_config import MAX_PAYLOAD_SIZE
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
    def __init__(self):
        self.log = get_class_logger(self)

        # 1. Socket Setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # --- CRITICAL FIX ---
        # Use Port 0 (Ephemeral) so the OS assigns a random available port.
        # This allows multiple SMTPClient instances to run in parallel threads.
        self.sock.bind((CLIENT_IP, 0))

        self.sock.settimeout(RDT_TIMEOUT)

        # 2. RDT Setup
        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False
        # self.log.info("SMTPClient initialized.")

    def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
        try:
            self._connect()
            self._do_handshake()
            self._send_mail_from(sender)
            self._send_rcpt_to(recipient)
            self._send_data(subject, body)
            self._send_quit()
            # self.log.info("Email transaction completed successfully.")
            return True
        except Exception as e:
            self.log.error(f"Email transaction failed: {e}")
            if self.is_connected:
                try:
                    self._send_command("QUIT")
                except:
                    pass
            return False
        finally:
            self._close()

    def _connect(self):
        self.receiver_gen = self.rdt_receiver.start_receiving()
        # Send empty packet to trigger server welcome
        self.rdt_sender.send(b"")
        code, msg = self._get_reply()
        if code != SMTP_READY:
            raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
        self.is_connected = True

    def _do_handshake(self):
        self._send_command("HELO localhost")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("HELO failed")

    def _send_mail_from(self, sender: str):
        self._send_command(f"MAIL FROM:<{sender}>")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("MAIL FROM failed")

    def _send_rcpt_to(self, recipient: str):
        self._send_command(f"RCPT TO:<{recipient}>")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("RCPT TO failed")

    def _send_data(self, subject: str, body: str):
        self._send_command("DATA")
        code, msg = self._get_reply()
        if code != SMTP_START_INPUT:
            raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

        # --- CHUNKING LOGIC ---
        full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
        payload_bytes = full_payload.encode("ascii")
        total_len = len(payload_bytes)
        sent = 0

        # self.log.debug(f"Sending {total_len} bytes in chunks of {MAX_PAYLOAD_SIZE}...")

        while sent < total_len:
            chunk = payload_bytes[sent : sent + MAX_PAYLOAD_SIZE]
            self.rdt_sender.send(chunk)
            sent += len(chunk)

        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

    def _send_quit(self):
        self._send_command("QUIT")
        try:
            self._get_reply()
        except:
            pass
        self.is_connected = False

    def _send_command(self, cmd: str):
        self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

    def _get_reply(self) -> Tuple[int, str]:
        # Always expects (data, addr) tuple now
        try:
            data_bytes, _ = next(self.receiver_gen)
            reply = data_bytes.decode("ascii").strip()

            if len(reply) < 3:
                raise SMTPProtocolError(f"Malformed reply: {reply}")

            code = int(reply[:3])
            msg = reply[4:] if len(reply) > 4 else ""
            return code, msg
        except StopIteration:
            raise SMTPConnectionError("Connection closed")

    def _close(self):
        if self.dispatcher:
            self.dispatcher.stop()
        if self.sock:
            self.sock.close()


# import socket
# from typing import Optional, Tuple
# from src.common.logger import get_class_logger
# from src.config import (
#     SMTP_SERVER_HOST,
#     SMTP_SERVER_PORT,
#     CLIENT_IP,
#     CLIENT_LISTENING_PORT,
#     RDT_TIMEOUT,
# )
# from src.rdt.rdt_config import MAX_PAYLOAD_SIZE
# from src.common.exceptions import SMTPProtocolError, SMTPConnectionError
# from src.rdt.rdt_sender import RDTSender
# from src.rdt.rdt_receiver import RDTReceiver
# from src.rdt.rdt_dispatcher import RDTDispatcher

# # SMTP Response Codes
# SMTP_READY = 220
# SMTP_OK = 250
# SMTP_CLOSING = 221
# SMTP_START_INPUT = 354


# class SMTPClient:
#     def __init__(self):
#         self.log = get_class_logger(self)

#         # 1. Socket Setup
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         self.sock.bind((CLIENT_IP, CLIENT_LISTENING_PORT))
#         self.sock.settimeout(RDT_TIMEOUT)

#         # 2. RDT Setup
#         self.dispatcher = RDTDispatcher(self.sock)
#         self.dispatcher.start()

#         self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)

#         # REMOVED confusing yield_addr=False flag.
#         self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
#         self.receiver_gen = self.rdt_receiver.start_receiving()

#         self.is_connected = False
#         self.log.info("SMTPClient initialized.")

#     def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
#         try:
#             self._connect()
#             self._do_handshake()
#             self._send_mail_from(sender)
#             self._send_rcpt_to(recipient)
#             self._send_data(subject, body)
#             self._send_quit()
#             self.log.info("Email transaction completed successfully.")
#             return True
#         except Exception as e:
#             self.log.error(f"Email transaction failed: {e}")
#             if self.is_connected:
#                 try:
#                     self._send_command("QUIT")
#                 except:
#                     pass
#             return False
#         finally:
#             self._close()

#     def _connect(self):
#         self.receiver_gen = self.rdt_receiver.start_receiving()
#         # Send empty packet to trigger server welcome
#         self.rdt_sender.send(b"")
#         code, msg = self._get_reply()
#         if code != SMTP_READY:
#             raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
#         self.is_connected = True

#     def _do_handshake(self):
#         self._send_command("HELO localhost")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("HELO failed")

#     def _send_mail_from(self, sender: str):
#         self._send_command(f"MAIL FROM:<{sender}>")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("MAIL FROM failed")

#     def _send_rcpt_to(self, recipient: str):
#         self._send_command(f"RCPT TO:<{recipient}>")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("RCPT TO failed")

#     def _send_data(self, subject: str, body: str):
#         self._send_command("DATA")
#         code, msg = self._get_reply()
#         if code != SMTP_START_INPUT:
#             raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

#         # --- CHUNKING LOGIC ---
#         full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
#         payload_bytes = full_payload.encode("ascii")
#         total_len = len(payload_bytes)
#         sent = 0

#         self.log.debug(f"Sending {total_len} bytes in chunks of {MAX_PAYLOAD_SIZE}...")

#         while sent < total_len:
#             chunk = payload_bytes[sent : sent + MAX_PAYLOAD_SIZE]
#             self.rdt_sender.send(chunk)
#             sent += len(chunk)

#         code, msg = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

#     def _send_quit(self):
#         self._send_command("QUIT")
#         try:
#             self._get_reply()
#         except:
#             pass
#         self.is_connected = False

#     def _send_command(self, cmd: str):
#         self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

#     def _get_reply(self) -> Tuple[int, str]:
#         # Always expects (data, addr) tuple now
#         try:
#             data_bytes, _ = next(self.receiver_gen)
#             reply = data_bytes.decode("ascii").strip()

#             if len(reply) < 3:
#                 raise SMTPProtocolError(f"Malformed reply: {reply}")

#             code = int(reply[:3])
#             msg = reply[4:] if len(reply) > 4 else ""
#             return code, msg
#         except StopIteration:
#             raise SMTPConnectionError("Connection closed")

#     def _close(self):
#         if self.dispatcher:
#             self.dispatcher.stop()
#         if self.sock:
#             self.sock.close()
