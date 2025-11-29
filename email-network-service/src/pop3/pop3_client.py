import socket
from typing import List, Tuple
from src.common.logger import get_class_logger
from src.config import (
    POP3_SERVER_HOST,
    POP3_SERVER_PORT,
    CLIENT_IP,
    CLIENT_LISTENING_PORT,
    RDT_TIMEOUT,
)
from src.common.exceptions import POP3ConnectionError, POP3ProtocolError
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_receiver import RDTReceiver


class POP3Client:
    def __init__(self):
        self.log = get_class_logger(self)

        # Create and bind the shared socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Use a different port than SMTP
        self.sock.bind((CLIENT_IP, CLIENT_LISTENING_PORT + 1))
        self.sock.settimeout(RDT_TIMEOUT)

        self.rdt_sender = RDTSender(POP3_SERVER_HOST, POP3_SERVER_PORT, self.sock)

        self.rdt_receiver = RDTReceiver(
            listen_host=None, listen_port=None, sock=self.sock, yield_addr=False
        )
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False
        self.log.info("POP3Client initialized with a shared socket.")

    def connect(self):
        self.log.debug("Starting RDT receiver and waiting for POP3 connection...")
        try:
            self.receiver_gen = self.rdt_receiver.start_receiving()
            # Initiate connection by sending an empty packet
            self.rdt_sender.send(b"")
            reply = self._get_reply()
            if not reply.startswith("+OK"):
                raise POP3ConnectionError(f"Server not ready. Got: {reply}")
            self.is_connected = True
            self.log.info(f"Connected to POP3 Server: {reply}")
        except Exception as e:
            self.log.error(f"Failed to connect to POP3 server: {e}")
            raise POP3ConnectionError(f"Connection failed: {e}")

    def authenticate(self, user: str, password: str):
        self._send_command(f"USER {user}")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"USER command failed: {reply}")

        self._send_command(f"PASS {password}")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"PASS command failed: {reply}")
        self.log.info(f"Successfully authenticated as {user}")

    def stat(self) -> Tuple[int, int]:
        self._send_command("STAT")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"STAT command failed: {reply}")
        parts = reply.split()
        return int(parts[1]), int(parts[2])

    def list(self) -> List[Tuple[int, int]]:
        self._send_command("LIST")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"LIST command failed: {reply}")

        messages = []
        while True:
            line = self._get_reply()
            if line == ".":
                break
            parts = line.split()
            messages.append((int(parts[0]), int(parts[1])))
        return messages

    def retr(self, msg_num: int) -> str:
        self._send_command(f"RETR {msg_num}")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"RETR command failed: {reply}")

        email_lines = []
        while True:
            line = self._get_reply()
            if line == ".":
                break
            email_lines.append(line)
        return "\n".join(email_lines)

    def dele(self, msg_num: int):
        self._send_command(f"DELE {msg_num}")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"DELE command failed: {reply}")

    def quit(self):
        if not self.is_connected:
            return
        self._send_command("QUIT")
        try:
            reply = self._get_reply()
            if not reply.startswith("+OK"):
                self.log.warning(f"QUIT command did not receive +OK: {reply}")
        except POP3ConnectionError:
            self.log.warning("Connection closed before QUIT was acknowledged.")
        finally:
            self.is_connected = False
            self._close()

    def _send_command(self, cmd: str):
        full_cmd = cmd + "\r\n"
        self.log.debug(f">>> {cmd}")
        self.rdt_sender.send(full_cmd.encode("ascii"))

    def _get_reply(self) -> str:
        self.log.debug("Waiting for response...")
        try:
            packet = next(self.receiver_gen)

            # receiver may or may not send address tuple depending on yield_addr flag
            if isinstance(packet, tuple):
                data_bytes, _addr = packet
            else:
                data_bytes = packet

            reply_str = data_bytes.decode("ascii").strip()

            self.log.debug(f"<<< {reply_str}")
            return reply_str
        except StopIteration:
            raise POP3ConnectionError("Connection closed unexpectedly.")

    def _close(self):
        self.log.debug("Closing RDT resources.")
        if self.rdt_receiver:
            self.rdt_receiver.stop()
        if self.rdt_sender:
            self.rdt_sender.close()

        if self.sock:
            self.sock.close()

        self.is_connected = False

    def fetch_new_emails(self, user, password) -> List[str]:
        try:
            self.connect()
            self.authenticate(user, password)

            _, total_size = self.stat()
            if total_size == 0:
                return []

            messages_info = self.list()

            emails = []
            for msg_num, _ in messages_info:
                email_content = self.retr(msg_num)
                emails.append(email_content)
                self.dele(msg_num)
            return emails
        finally:
            self.quit()
