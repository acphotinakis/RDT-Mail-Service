import re
import threading
from enum import Enum, auto
from typing import Optional, Tuple, Dict, Any
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from email.parser import BytesParser
from email.policy import default as email_policy

from src.common.logger import get_class_logger
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_dispatcher import RDTDispatcher
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User
from src.models.email_data import EmailData
from src.auth.user_manager import UserManager

SMTP_EOL = b"\r\n"
SMTP_TERMINATOR = b"\r\n.\r\n"
_re_cmd = re.compile(r"^([A-Za-z]+)(?:\s+(.*))?$")


class SMTPState(Enum):
    WAIT_FOR_HELO = auto()
    WAIT_FOR_MAIL_FROM = auto()
    WAIT_FOR_RCPT_TO = auto()
    WAIT_FOR_DATA_CMD = auto()
    READING_DATA_STREAM = auto()


def _parse_angle_addr(arg: str) -> Optional[str]:
    if not arg:
        return None
    arg = arg.strip()
    if arg.startswith("<") and arg.endswith(">"):
        arg = arg[1:-1].strip()
    return arg if "@" in arg else None


class SMTPServer:

    def __init__(self, host: str, port: int):
        self.log = get_class_logger(self)
        self.log.info("Initializing SMTP server module...")

        self.host = host
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        self.dispatcher = RDTDispatcher(self.sock)
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)

        self._senders: Dict[Tuple[str, int], RDTSender] = {}
        self.storage = StorageManager()
        self._running = False
        self._thread = None

        self.log.info(f"SMTP server initialized on {self.host}:{self.port}")
        self.log.info(self.to_string())

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
            sender.send(msg.encode("ascii"))
            self.log.debug(f"[SMTP → {addr}] {msg.strip()}")
        except ConnectionError:
            self.log.error(f"Failed to send reply to {addr}. Client likely disconnected.")
        except Exception as e:
            self.log.exception(f"Unexpected error sending reply to {addr}: {e}")

    def _create_session(self) -> Dict[str, Any]:
        return {
            "state": SMTPState.WAIT_FOR_HELO,
            "mail_from": None,
            "rcpt_to": [],
            "data_buffer": bytearray(),
            "line_buffer": bytearray(),
        }

    def _cleanup_session(self, addr: Tuple[str, int], sessions: Dict, last_activity: Dict) -> None:
        """
        Removes a client session and cleans up associated resources.

        This method is called when a client sends QUIT or when a session times out.
        It ensures memory is freed and the RDT layer is reset for that address.
        """
        if addr in sessions:
            self.log.info(f"Cleaning up session for {addr}")
            del sessions[addr]

        if addr in last_activity:
            del last_activity[addr]

        # Clean up the RDT sender associated with this client
        if addr in self._senders:
            del self._senders[addr]

        # Critical: Reset RDT receiver state so a future reconnect
        # (starting with Seq 0) isn't mistaken for a duplicate.
        self.rdt_receiver.reset_state(addr)

    def _serve_loop(self):
        """
        The main server loop that listens for and processes client packets.

        This implementation uses a ThreadPoolExecutor to handle commands concurrently,
        preventing disk I/O (like saving emails) from blocking the main network loop.
        It also implements a 'reaper' strategy to clean up inactive sessions.
        """
        self.log.info("SMTP serve loop running...")

        self.dispatcher.start()

        # Local state for the loop
        sessions: Dict[Tuple[str, int], Dict] = {}
        last_activity: Dict[Tuple[str, int], float] = {}

        # Configuration
        SESSION_TIMEOUT = 300  # 5 minutes
        MAX_WORKERS = 10  # Max concurrent commands

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Continuously fetch packets from the RDT Receiver
            for packet in self.rdt_receiver.start_receiving():

                if not self._running:
                    break

                try:
                    data, addr = packet
                except Exception:
                    self.log.error("Invalid packet received (missing sender address).")
                    continue

                # 1. Update Session Activity
                last_activity[addr] = time.time()

                # 2. Session Timeout Reaper
                # Check for stale sessions periodically
                now = time.time()
                # Identify sessions inactive for > SESSION_TIMEOUT
                # Note: creating a list to avoid changing dict size during iteration
                stale_addrs = [
                    a for a, last_ts in last_activity.items() if now - last_ts > SESSION_TIMEOUT
                ]

                for stale in stale_addrs:
                    self.log.warning(f"Session timed out for client {stale}")
                    self._cleanup_session(stale, sessions, last_activity)

                # 3. Session Initialization
                if addr not in sessions:
                    sessions[addr] = self._create_session()
                    self._send_reply(addr, "220 Welcome Simple SMTP Server")
                    self.log.info(f"New SMTP session created for client {addr}")

                # 4. Dispatch Processing to Worker Thread
                # We submit the work to the pool so the main loop can immediately
                # fetch the next packet from other clients.
                executor.submit(self._process_packet, addr, data, sessions)

        self._cleanup_senders()
        self.log.info("SMTP serve loop fully terminated.")

    def _process_packet(self, addr, data, sessions):
        """
        Helper method to process a packet within a worker thread.
        This encapsulates the logic previously inside the main loop.
        """
        # Guard against session deletion (race condition with reaper)
        if addr not in sessions:
            return

        session = sessions[addr]

        try:
            self.log.debug(f"Received {len(data)} bytes from {addr}")

            if session["state"] == SMTPState.READING_DATA_STREAM:
                self._handle_data_stream(addr, session, data)
            else:
                self._handle_command_stream(addr, session, data, sessions)

        except Exception as e:
            self.log.exception(f"Error processing packet for {addr}: {e}")
            self._send_reply(addr, "500 Internal Server Error")

    def _handle_data_stream(self, addr, session, data):
        session["data_buffer"].extend(data)
        if SMTP_TERMINATOR not in session["data_buffer"]:
            return

        full = bytes(session["data_buffer"])
        idx = full.find(SMTP_TERMINATOR)
        msg_bytes = full[:idx]

        session["data_buffer"] = bytearray()
        session["line_buffer"] = bytearray()
        session["state"] = SMTPState.WAIT_FOR_MAIL_FROM

        self._finalize_message(addr, session, msg_bytes)

    def _finalize_message(self, addr, session, msg_bytes):
        try:
            parser = BytesParser(policy=email_policy)
            msg_obj = parser.parsebytes(msg_bytes)

            uid = msg_obj.get("Message-ID")
            if uid is None:
                import uuid, time

                uid = f"<{int(time.time())}-{uuid.uuid4().hex}>"

            recipients = session.get("rcpt_to", [])
            if not recipients:
                self._send_reply(addr, "550 No recipients")
                return

            rcpt_addr = recipients[0]
            username = rcpt_addr.split("@")[0]
            user_manager = UserManager()
            user = user_manager.get_user(username)

            if not user:
                self.log.warning(f"Rejected mail for unknown user: {username}")
                self._send_reply(addr, "550 No such user")
                return

            email_data = EmailData(
                raw_message=msg_obj,
                uid=uid,
                subject=msg_obj.get("Subject", ""),
                sender=msg_obj.get("From", ""),
                recipient=rcpt_addr,
                date=msg_obj.get("Date", ""),
                body_html=None,
                body_text=None,
            )

            saved_path = self.storage.save_email(user, email_data)
            if saved_path:
                self._send_reply(addr, "250 OK: Message accepted for delivery")
                session["rcpt_to"] = []
            else:
                self._send_reply(addr, "451 Local processing error")

        except Exception as e:
            self.log.exception(f"Error finalizing email DATA block: {e}")
            self._send_reply(addr, "451 Error processing message")

    def _handle_command_stream(self, addr, session, data, sessions):
        buf = session["line_buffer"]
        buf.extend(data)

        while True:
            idx = buf.find(b"\r\n")
            if idx == -1:
                return

            line = bytes(buf[:idx])
            del buf[: idx + 2]

            try:
                cmd_str = line.decode("ascii", errors="ignore").strip()
            except Exception:
                cmd_str = ""

            self.log.debug(f"[SMTP CMD from {addr}] {cmd_str!r}")

            m = _re_cmd.match(cmd_str)
            if not m:
                self._send_reply(addr, "500 Syntax error")
                continue

            verb = m.group(1).upper()
            arg = m.group(2) or ""

            handler = getattr(self, f"_cmd_{verb}", None)
            if handler:
                handler(addr, session, arg, sessions)
            else:
                self._send_reply(addr, "500 Command unrecognized")

    # --- SMTP Command Handlers ---
    def _cmd_HELO(self, addr, session, arg, sessions):
        session["state"] = SMTPState.WAIT_FOR_MAIL_FROM
        self._send_reply(addr, "250 Hello")

    _cmd_EHLO = _cmd_HELO

    def _cmd_MAIL(self, addr, session, arg, sessions):
        if session["state"] not in (
            SMTPState.WAIT_FOR_MAIL_FROM,
            SMTPState.WAIT_FOR_RCPT_TO,
        ):
            return self._send_reply(addr, "503 Bad sequence")
        if arg.upper().startswith("FROM:"):
            parsed = _parse_angle_addr(arg[5:].strip())
            if parsed:
                session["mail_from"] = parsed
                session["state"] = SMTPState.WAIT_FOR_RCPT_TO
                return self._send_reply(addr, "250 OK")
        self._send_reply(addr, "500 Syntax error in MAIL FROM")

    def _cmd_RCPT(self, addr, session, arg, sessions):
        if session["state"] != SMTPState.WAIT_FOR_RCPT_TO:
            return self._send_reply(addr, "503 Bad sequence")
        if arg.upper().startswith("TO:"):
            parsed = _parse_angle_addr(arg[3:].strip())
            if parsed:
                session["rcpt_to"].append(parsed)
                session["state"] = SMTPState.WAIT_FOR_DATA_CMD
                return self._send_reply(addr, "250 OK")
        self._send_reply(addr, "500 Syntax error in RCPT TO")

    def _cmd_DATA(self, addr, session, arg, sessions):
        if session["state"] != SMTPState.WAIT_FOR_DATA_CMD or not session["rcpt_to"]:
            return self._send_reply(addr, "503 Bad sequence")
        session["state"] = SMTPState.READING_DATA_STREAM
        session["data_buffer"] = bytearray()
        session["line_buffer"] = bytearray()
        self._send_reply(addr, "354 Start mail input; end with <CRLF>.<CRLF>")

    def _cmd_RSET(self, addr, session, arg, sessions):
        session.update(self._create_session())
        self._send_reply(addr, "250 OK")

    def _cmd_NOOP(self, addr, session, arg, sessions):
        self._send_reply(addr, "250 OK")

    def _cmd_QUIT(self, addr, session, arg, sessions):
        self._send_reply(addr, "221 Bye")

        # Cleanup Session
        self._senders.pop(addr, None)
        sessions.pop(addr, None)

        # Reset RDT State for this client so they can reconnect later with SEQ 0
        self.rdt_receiver.reset_state(addr)

    def _cleanup_senders(self):
        self._senders.clear()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread_start_time = time.time()
        self._thread = threading.Thread(
            target=self._serve_loop, name="smtp-serve-loop", daemon=True
        )
        self._thread.start()
        self.log.info("SMTP server started.")

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
        self.log.info("SMTP server stopped.")

    def to_string(self) -> str:
        """
        Returns a pretty-formatted overview of the POP3Server's configuration
        and runtime state. Useful for debugging, diagnostics, and health checks.
        """

        thread = self._thread
        dispatcher_thread = self.dispatcher._thread

        props = {
            "Host": self.host,
            "Port": self.port,
            "Running": self._running,
            "Socket Bound": f"{self.host}:{self.port}",
            # --- Thread Details ---
            "Thread Alive": thread.is_alive() if thread else False,
            "Thread Name": thread.name if thread else None,
            "Thread ID": thread.ident if thread else None,
            "Native Thread ID": (
                thread.native_id if thread and hasattr(thread, "native_id") else None
            ),
            "Thread Daemon": thread.daemon if thread else None,
            "Thread Uptime (s)": (
                round(time.time() - self._thread_start_time, 2)
                if thread and hasattr(self, "_thread_start_time")
                else None
            ),
            # --- Dispatcher Info ---
            "Dispatcher Thread Alive": (
                dispatcher_thread.is_alive() if dispatcher_thread else False
            ),
            "Receiver Running": getattr(self.rdt_receiver, "_running", None),
            # --- Storage & Users ---
            "Active Senders": len(self._senders),
            "Storage Backend": self.storage.__class__.__name__,
        }

        # Compute alignment width
        longest_key = max(len(k) for k in props.keys())
        lines = ["\nPOP3Server Configuration:"]
        lines.append("-" * (longest_key + 30))

        for key, value in props.items():
            lines.append(f"{key.ljust(longest_key)} : {value}")

        lines.append("-" * (longest_key + 30))

        msg = "\n".join(lines)
        return msg
