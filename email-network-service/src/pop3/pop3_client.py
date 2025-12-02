import socket
from typing import List, Tuple
from src.common.logger import *
from src.config import Config
from src.common.exceptions import POP3ConnectionError, POP3ProtocolError
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_dispatcher import RDTDispatcher


class POP3Client:
    def __init__(self):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # FIX: Bind to Port 0 (Ephemeral) to allow concurrent simulation threads
        self.sock.bind((Config.CLIENT_IP, 0))
        self.sock.settimeout(Config.RDT_TIMEOUT)

        self.is_connected = False

        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        self.rdt_sender = RDTSender(
            Config.POP3_SERVER_HOST, Config.POP3_SERVER_PORT, self.dispatcher
        )
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        log_info_detailed(
            f"POP3 client initialized on {self.sock.getsockname()[0]}:{self.sock.getsockname()[1]}"
        )
        log_info_detailed(self.to_string())

    def _get_reply(self) -> str:
        try:
            data_bytes, _ = next(self.receiver_gen)
            return data_bytes.decode("ascii").strip()
        except StopIteration:
            raise POP3ConnectionError("Connection closed unexpectedly.")

    def connect(self):
        self.receiver_gen = self.rdt_receiver.start_receiving()
        self.rdt_sender.send(b"")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ConnectionError(f"Server error: {reply}")
        self.is_connected = True

    def authenticate(self, user: str, password: str):
        self._send_command(f"USER {user}")
        if not self._get_reply().startswith("+OK"):
            raise POP3ProtocolError("USER failed")
        self._send_command(f"PASS {password}")
        if not self._get_reply().startswith("+OK"):
            raise POP3ProtocolError("PASS failed")

    def stat(self) -> Tuple[int, int]:
        self._send_command("STAT")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError(f"STAT failed: {reply}")
        parts = reply.split()
        return int(parts[1]), int(parts[2])

    def list(self) -> List[Tuple[int, int]]:
        self._send_command("LIST")
        reply = self._get_reply()
        if not reply.startswith("+OK"):
            raise POP3ProtocolError("LIST failed")
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
            raise POP3ProtocolError("RETR failed")
        lines = []
        while True:
            line = self._get_reply()
            if line == ".":
                break
            lines.append(line)
        return "\n".join(lines)

    def dele(self, msg_num: int):
        self._send_command(f"DELE {msg_num}")
        if not self._get_reply().startswith("+OK"):
            raise POP3ProtocolError("DELE failed")

    def quit(self):
        if self.is_connected:
            self._send_command("QUIT")
            try:
                self._get_reply()
            except:
                pass
            self._close()

    def _send_command(self, cmd: str):
        self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

    def _close(self):
        self.dispatcher.stop()
        self.sock.close()
        self.is_connected = False

    # --- High Level Helper for Simulation ---
    def get_all_messages(self, username, password) -> List[str]:
        """
        Connects, authenticates, retrieves all emails, deletes them, and quits.
        Returns a list of raw email strings.
        """
        try:
            self.connect()
            self.authenticate(username, password)

            _, total_size = self.stat()
            if total_size == 0:
                return []

            messages_info = self.list()
            emails = []
            for msg_num, _ in messages_info:
                content = self.retr(msg_num)
                emails.append(content)
                self.dele(msg_num)

            return emails
        except Exception as e:
            log_error_detailed(f"Error fetching messages: {e}")
            return []
        finally:
            self.quit()

    def to_string(self) -> str:
        """
        Returns a diagnostic summary of the POP3Client state.
        """
        sock_info = None
        try:
            sock_info = self.sock.getsockname()
        except Exception:
            sock_info = "(unbound)"

        props = {
            "Connected": self.is_connected,
            "Local Address": sock_info,
            "Server Address": f"{Config.POP3_SERVER_HOST}:{Config.POP3_SERVER_PORT}",
            "RDT Sender Seq": getattr(self.rdt_sender, "curr_seq", None),
            "Dispatcher Running": self.dispatcher.running,
            "Receiver Active": self.rdt_receiver.running,
        }

        longest = max(len(k) for k in props)
        lines = ["\nPOP3Client State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
