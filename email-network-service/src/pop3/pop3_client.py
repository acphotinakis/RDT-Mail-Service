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
from src.rdt.rdt_dispatcher import RDTDispatcher


class POP3Client:
    def __init__(self):
        self.log = get_class_logger(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((CLIENT_IP, CLIENT_LISTENING_PORT + 1))
        self.sock.settimeout(RDT_TIMEOUT)

        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        self.rdt_sender = RDTSender(POP3_SERVER_HOST, POP3_SERVER_PORT, self.dispatcher)
        # Standardized receiver
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False

    def _get_reply(self) -> str:
        try:
            # Unpack tuple always
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

    def _send_command(self, cmd: str):
        self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

    def quit(self):
        if self.is_connected:
            self._send_command("QUIT")
            try:
                self._get_reply()
            except:
                pass
            self._close()

    def _close(self):
        self.dispatcher.stop()
        self.sock.close()
        self.is_connected = False
