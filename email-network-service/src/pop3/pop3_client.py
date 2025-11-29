from typing import List, Tuple
from common.logger import get_class_logger
from common.config import POP3_SERVER_HOST, POP3_SERVER_PORT, CLIENT_IP, CLIENT_LISTENING_PORT
from common.exceptions import POP3ConnectionError, POP3ProtocolError
from rdt.rdt_sender import RDTSender
from rdt.rdt_receiver import RDTReceiver


class POP3Client:
    def __init__(self):
        self.log = get_class_logger(self)
        self.rdt_sender = RDTSender(POP3_SERVER_HOST, POP3_SERVER_PORT)
        self.rdt_receiver = RDTReceiver(
            CLIENT_IP, CLIENT_LISTENING_PORT + 1
        )  # Use a different port than SMTP
        self.receiver_gen = None
        self.is_connected = False

    def connect(self):
        self.log.debug("Starting RDT receiver and waiting for POP3 connection...")
        try:
            self.receiver_gen = self.rdt_receiver.start_receiving()
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
        self._send_command("QUIT")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            self.log.warning(f"QUIT command did not receive +OK: {reply}")
        self.is_connected = False
        self._close()

    def _send_command(self, cmd: str):
        full_cmd = cmd + "\r\n"
        self.log.debug(f">>> {cmd}")
        self.rdt_sender.send(full_cmd.encode("ascii"))

    def _get_reply(self) -> str:
        self.log.debug("Waiting for response...")
        data_bytes = next(self.receiver_gen)
        reply_str = data_bytes.decode("ascii").strip()
        self.log.debug(f"<<< {reply_str}")
        return reply_str

    def _close(self):
        self.log.debug("Closing RDT resources.")
        if self.rdt_receiver:
            self.rdt_receiver.stop()
        if self.rdt_sender:
            self.rdt_sender.close()
        self.is_connected = False

    def fetch_new_emails(self, user, password) -> List[str]:
        self.connect()
        self.authenticate(user, password)

        _, total_size = self.stat()
        if total_size == 0:
            self.quit()
            return []

        messages_info = self.list()

        emails = []
        for msg_num, _ in messages_info:
            email_content = self.retr(msg_num)
            emails.append(email_content)
            self.dele(msg_num)

        self.quit()
        return emails
