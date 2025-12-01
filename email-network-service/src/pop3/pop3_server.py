import threading
from typing import Optional, Tuple, Dict, Any, List

from src.common.logger import get_class_logger
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_dispatcher import RDTDispatcher
from src.mailbox.storage_manager import StorageManager
from src.auth.user_manager import UserManager
from src.auth.user import User
import socket


class POP3Server:
    def __init__(self, host: str, port: int):
        self.log = get_class_logger(self)
        self.log.info("Initializing POP3 server module...")
        self.host = host
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        self.dispatcher = RDTDispatcher(self.sock)
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)

        self._senders: Dict[Tuple[str, int], RDTSender] = {}
        self.storage = StorageManager()
        self.user_manager = UserManager()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.log.info(f"POP3 server initialized on {self.host}:{self.port}")

    def _get_sender(self, addr: Tuple[str, int]) -> RDTSender:
        if addr not in self._senders:
            host, port = addr
            self.log.debug(f"Allocating new RDTSender for {addr}")
            self._senders[addr] = RDTSender(host, port, self.dispatcher)
        return self._senders[addr]

    def _send_reply(self, addr: Tuple[str, int], msg: str):
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        try:
            sender = self._get_sender(addr)
            sender.send(msg.encode("ascii", errors="replace"))
            self.log.debug(f"[POP3 → {addr}] {msg.strip()}")
        except ConnectionError:
            self.log.error(f"Failed to reply to {addr}. Connection lost.")
        except Exception as e:
            self.log.exception(f"Error sending POP3 reply to {addr}: {e}")

    def _create_session(self) -> Dict[str, Any]:
        return {
            "state": "AUTHORIZATION",
            "user": None,
            "marked_for_deletion": set(),
        }

    def _serve_loop(self):
        self.log.info("POP3 serve loop running...")

        self.dispatcher.start()

        sessions: Dict[Tuple[str, int], Dict] = {}

        for packet in self.rdt_receiver.start_receiving():
            if not self._running:
                break

            try:
                data, addr = packet
            except Exception:
                continue

            if addr not in sessions:
                sessions[addr] = self._create_session()
                self._send_reply(addr, "+OK POP3 server ready")
                self.log.info(f"New POP3 session created for client {addr}")

            session = sessions[addr]
            lines = data.decode("ascii", errors="ignore").split("\r\n")
            for line in lines:
                if not line:
                    continue
                self.log.debug(f"[POP3 CMD from {addr}] {line!r}")
                self._handle_command(addr, session, line, sessions)

    def _handle_command(self, addr, session, line, sessions):
        parts = line.strip().split()
        if not parts:
            return
        command = parts[0].upper()
        args = parts[1:]

        handler = getattr(self, f"_cmd_{command}", None)
        if handler:
            handler(addr, session, args)
        else:
            self._send_reply(addr, "-ERR Unknown command")

    def _cmd_USER(self, addr, session, args):
        if session["state"] != "AUTHORIZATION":
            return self._send_reply(addr, "-ERR Command not allowed here")
        if not args:
            return self._send_reply(addr, "-ERR Missing argument")

        username = args[0]
        if self.user_manager.get_user(username):
            session["user"] = username
            self._send_reply(addr, f"+OK User {username} accepted")
        else:
            self._send_reply(addr, "-ERR No such user")

    def _cmd_PASS(self, addr, session, args):
        if session["state"] != "AUTHORIZATION" or not session["user"]:
            return self._send_reply(addr, "-ERR Command not allowed here")

        if not args:
            return self._send_reply(addr, "-ERR Missing password")

        password = args[0]
        username = session["user"]

        # Verify credentials using UserManager
        user = self.user_manager.authenticate(username, password)

        if user:
            session["state"] = "TRANSACTION"
            self._send_reply(addr, "+OK Mailbox open")
        else:
            session["user"] = None  # Reset user on failure to force re-auth
            self._send_reply(addr, "-ERR Invalid credentials")

    def _cmd_STAT(self, addr, session, args):
        if session["state"] != "TRANSACTION":
            return self._send_reply(addr, "-ERR Command not allowed here")
        user = User(session["user"])
        messages = self.storage.list_messages(user)
        undeleted_messages = [
            msg for i, msg in enumerate(messages, 1) if i not in session["marked_for_deletion"]
        ]
        total_size = sum(msg[1] for msg in undeleted_messages)
        self._send_reply(addr, f"+OK {len(undeleted_messages)} {total_size}")

    def _cmd_LIST(self, addr, session, args):
        if session["state"] != "TRANSACTION":
            return self._send_reply(addr, "-ERR Command not allowed here")
        user = User(session["user"])
        messages = self.storage.list_messages(user)

        if not args:
            self._send_reply(addr, f"+OK {len(messages)} messages")
            for i, msg in enumerate(messages, 1):
                if i not in session["marked_for_deletion"]:
                    self._send_reply(addr, f"{i} {msg[1]}")
            self._send_reply(addr, ".")
        else:
            try:
                msg_num = int(args[0])
                if 1 <= msg_num <= len(messages) and msg_num not in session["marked_for_deletion"]:
                    size = messages[msg_num - 1][1]
                    self._send_reply(addr, f"+OK {msg_num} {size}")
                else:
                    self._send_reply(addr, f"-ERR No such message")
            except (ValueError, IndexError):
                self._send_reply(addr, "-ERR Invalid message number")

    def _cmd_RETR(self, addr, session, args):
        if session["state"] != "TRANSACTION":
            return self._send_reply(addr, "-ERR Command not allowed here")
        if not args:
            return self._send_reply(addr, "-ERR Missing argument")

        try:
            msg_num = int(args[0])
            user = User(session["user"])
            messages = self.storage.list_messages(user)
            if 1 <= msg_num <= len(messages) and msg_num not in session["marked_for_deletion"]:
                filename = messages[msg_num - 1][0]
                content = self.storage.get_message_content(user, filename)
                if content:
                    self._send_reply(addr, f"+OK {len(content)} octets")
                    self._get_sender(addr).send(content.encode("ascii"))
                    self._send_reply(addr, ".")
                else:
                    self._send_reply(addr, f"-ERR could not retrieve message")
            else:
                self._send_reply(addr, f"-ERR No such message")
        except (ValueError, IndexError):
            self._send_reply(addr, "-ERR Invalid message number")

    def _cmd_DELE(self, addr, session, args):
        if session["state"] != "TRANSACTION":
            return self._send_reply(addr, "-ERR Command not allowed here")
        try:
            msg_num = int(args[0])
            user = User(session["user"])
            messages = self.storage.list_messages(user)
            if 1 <= msg_num <= len(messages) and msg_num not in session["marked_for_deletion"]:
                session["marked_for_deletion"].add(msg_num)
                self._send_reply(addr, f"+OK Message {msg_num} deleted")
            else:
                self._send_reply(addr, f"-ERR Message {msg_num} already deleted or does not exist")
        except (ValueError, IndexError):
            self._send_reply(addr, "-ERR Invalid message number")

    def _cmd_QUIT(self, addr, session, args):
        user = User(session["user"])
        if session["state"] == "TRANSACTION":
            messages = self.storage.list_messages(user)
            marked_for_deletion = sorted(list(session["marked_for_deletion"]), reverse=True)
            for msg_num in marked_for_deletion:
                filename = messages[msg_num - 1][0]
                self.storage.delete_email(user, filename)

        self._send_reply(addr, "+OK POP3 server signing off")
        self._senders.pop(addr, None)
        # Reset RDT state for this client
        self.rdt_receiver.reset_state(addr)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._serve_loop, name="pop3-serve-loop", daemon=True
        )
        self._thread.start()
        self.log.info("POP3 server started.")

    def stop(self):
        if not self._running:
            return
        self._running = False
        try:
            self.dispatcher.stop()
        except Exception:
            self.log.exception("Error stopping Dispatcher")
        if self._thread:
            self._thread.join(timeout=2.0)
        self.log.info("POP3 server stopped.")
