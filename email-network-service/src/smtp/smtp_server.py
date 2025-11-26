# Path: src/smtp/smtp_server.py

import re
import threading
from enum import Enum, auto
from typing import Optional, Tuple, Dict, Any

from email.parser import BytesParser
from email.policy import default as email_policy

from src.common.logger import get_class_logger
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_sender import RDTSender
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User
from src.client.frontend.models import EmailData

SMTP_EOL = b"\r\n"
SMTP_TERMINATOR = b"\r\n.\r\n"
_re_cmd = re.compile(r"^([A-Za-z]+)(?:\s+(.*))?$")


# ------------------------------------------------------------
# ENUM: SMTP STATE
# ------------------------------------------------------------
class SMTPState(Enum):
    WAIT_FOR_HELO = auto()
    WAIT_FOR_MAIL_FROM = auto()
    WAIT_FOR_RCPT_TO = auto()
    WAIT_FOR_DATA_CMD = auto()
    READING_DATA_STREAM = auto()


def _parse_angle_addr(arg: str) -> Optional[str]:
    """Parse <user@domain> or raw user@domain."""
    if not arg:
        return None

    arg = arg.strip()

    if arg.startswith("<") and arg.endswith(">"):
        arg = arg[1:-1].strip()

    return arg if "@" in arg else None


# ============================================================
#                   SMTP SERVER (CLEAN VERSION)
# ============================================================
class SMTPServer:

    # ------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------
    def __init__(self, host: str, port: int):
        self.log = get_class_logger(self)
        self.log.info("Initializing SMTP server module...")

        self.host = host
        self.port = port

        self.rdt_receiver = RDTReceiver(host, port)
        self._senders: Dict[Tuple[str, int], RDTSender] = {}

        self.storage = StorageManager()

        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.log.info(f"SMTP server initialized on {self.host}:{self.port}")

    # ------------------------------------------------------------
    # SENDER MANAGEMENT
    # ------------------------------------------------------------
    def _get_sender(self, addr: Tuple[str, int]) -> RDTSender:
        if addr not in self._senders:
            host, port = addr
            self.log.debug(f"Allocating new RDTSender for {addr}")
            self._senders[addr] = RDTSender(host, port)
        return self._senders[addr]

    def _send_reply(self, addr: Tuple[str, int], msg: str):
        if not msg.endswith("\r\n"):
            msg += "\r\n"

        try:
            sender = self._get_sender(addr)
            sender.send(msg.encode("ascii", errors="replace"))
            self.log.debug(f"[SMTP → {addr}] {msg.strip()}")
        except Exception as e:
            self.log.exception(f"Error sending SMTP reply to {addr}: {e}")

    # ------------------------------------------------------------
    # SESSION MGMT
    # ------------------------------------------------------------
    def _create_session(self) -> Dict[str, Any]:
        """Return a fresh, empty SMTP session structure."""
        return {
            "state": SMTPState.WAIT_FOR_HELO,
            "mail_from": None,
            "rcpt_to": [],
            "data_buffer": bytearray(),
            "line_buffer": bytearray(),
        }

    # ------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------
    def _serve_loop(self):
        self.log.info("SMTP serve loop running...")

        sessions: Dict[Tuple[str, int], Dict] = {}

        for packet in self.rdt_receiver.start_receiving():

            if not self._running:
                break

            try:
                data, addr = packet
            except Exception:
                self.log.error("Invalid packet received (missing sender address).")
                continue

            self.log.debug(f"Received {len(data)} bytes from {addr}")

            # Ensure session exists
            if addr not in sessions:
                sessions[addr] = self._create_session()
                self._send_reply(addr, "220 Welcome Simple SMTP Server")
                self.log.info(f"New SMTP session created for client {addr}")

            session = sessions[addr]

            # State-machine routing
            if session["state"] == SMTPState.READING_DATA_STREAM:
                self._handle_data_stream(addr, session, data)
                continue

            # Otherwise, handle commands
            self._handle_command_stream(addr, session, data, sessions)

        self._cleanup_senders()
        self.log.info("SMTP serve loop fully terminated.")

    # ------------------------------------------------------------
    # DATA MODE HANDLER (DATA … <CRLF>.<CRLF>)
    # ------------------------------------------------------------
    def _handle_data_stream(self, addr, session, data):
        session["data_buffer"].extend(data)

        if SMTP_TERMINATOR not in session["data_buffer"]:
            self.log.debug("DATA mode active — waiting for terminator.")
            return

        # Extract raw message
        full = bytes(session["data_buffer"])
        idx = full.find(SMTP_TERMINATOR)
        msg_bytes = full[:idx]

        self.log.debug(f"DATA terminator received at {addr}. Size={len(msg_bytes)}")

        # Reset for new transactions
        session["data_buffer"] = bytearray()
        session["line_buffer"] = bytearray()
        session["state"] = SMTPState.WAIT_FOR_MAIL_FROM

        self._finalize_message(addr, session, msg_bytes)

    # ------------------------------------------------------------
    # FINALIZE AND SAVE EMAIL
    # ------------------------------------------------------------
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
                self.log.warning("DATA completed but session had no RCPT TO entries.")
                return

            rcpt_addr = recipients[0]
            username = rcpt_addr.split("@")[0]
            user = User(username)

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
                self.log.info(f"Message stored for {rcpt_addr} at {saved_path}")
                session["rcpt_to"] = []
            else:
                self._send_reply(addr, "451 Local processing error")
                self.log.error("StorageManager returned failure.")

        except Exception as e:
            self.log.exception(f"Error finalizing email DATA block: {e}")
            self._send_reply(addr, "451 Error processing message")

    # ------------------------------------------------------------
    # COMMAND PROCESSOR
    # ------------------------------------------------------------
    def _handle_command_stream(self, addr, session, data, sessions):
        buf = session["line_buffer"]
        buf.extend(data)

        while True:
            idx = buf.find(b"\r\n")
            if idx == -1:
                return  # Wait for more bytes

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
                self.log.warning(f"Unknown SMTP verb: {verb}")
                self._send_reply(addr, "500 Command unrecognized")

    # ------------------------------------------------------------
    # SMTP COMMAND HANDLERS
    # ------------------------------------------------------------

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
        self.log.info(f"Client {addr} terminated session.")

        try:
            self._senders[addr].close()
        except Exception:
            pass

        self._senders.pop(addr, None)
        sessions.pop(addr, None)

    # ------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------
    def _cleanup_senders(self):
        for sender in self._senders.values():
            try:
                sender.close()
            except Exception:
                self.log.exception("Error closing RDTSender")
        self._senders.clear()

    # ------------------------------------------------------------
    # PUBLIC START/STOP
    # ------------------------------------------------------------
    def start(self):
        if self._running:
            return self.log.warning("SMTP already running")

        self._running = True
        self._thread = threading.Thread(
            target=self._serve_loop, name="smtp-serve-loop", daemon=True
        )
        self._thread.start()
        self.log.info("SMTP server started in background thread.")

    def stop(self):
        if not self._running:
            return self.log.warning("SMTP not running")

        self._running = False
        try:
            self.rdt_receiver.stop()
        except Exception:
            self.log.exception("Error stopping RDTReceiver")

        if self._thread:
            self._thread.join(timeout=2.0)

        self.log.info("SMTP server fully stopped.")
