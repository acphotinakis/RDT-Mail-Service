import os
from src.common.logger import *


class Config:
    """
    Central OOP-based configuration object for the email system.
    All settings are class-level constants and may be overridden
    at runtime via CLI arguments (see apply_args()).
    """

    # ==============================================================
    # Directory Layout
    # ==============================================================
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATABASE_PATH = os.path.join(BASE_DIR, "database")
    USER_DB_FILE = os.path.join(DATABASE_PATH, "users.json")
    MAILBOXES_DIR = os.path.join(DATABASE_PATH, "mailboxes")
    TEMP_EMAILS_DIR = os.path.join(DATABASE_PATH, "temp")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")

    # ==============================================================
    # Simulation Defaults
    # ==============================================================
    NUM_USERS = 10
    NUM_EMAILS_PER_USER = 10
    CONCURRENCY = 5
    DELAY_BETWEEN_SENDS = 0.1
    MESSAGE_SIZE = 256  # bytes (approx subject+body)

    # ==============================================================
    # Network Config
    # ==============================================================
    SERVER_BIND_IP = "127.0.0.1"
    SMTP_SERVER_HOST = SERVER_BIND_IP
    SMTP_SERVER_PORT = 2525
    POP3_SERVER_HOST = SERVER_BIND_IP
    POP3_SERVER_PORT = 1100
    CLIENT_IP = "127.0.0.1"
    CLIENT_LISTENING_PORT = 2526

    # ==============================================================
    # RDT Layer
    # ==============================================================
    RDT_TIMEOUT = 1.0
    RDT_WINDOW_SIZE = 10
    RDT_RECV_BUFSIZE = 4096
    MAX_PAYLOAD_SIZE = 1024

    # Logging
    LOG_LEVEL = "DEBUG"

    # Auto Login File
    AUTOLOGIN_FILE = ".autologin.json"

    # ==============================================================
    # Apply CLI Arguments to Config
    # ==============================================================
    @classmethod
    def apply_args(cls, args):
        if args.num_users:
            cls.NUM_USERS = int(args.num_users)
        if args.num_emails:
            cls.NUM_EMAILS_PER_USER = int(args.num_emails)
        if args.concurrency:
            cls.CONCURRENCY = int(args.concurrency)
        if args.delay_between_sends:
            cls.DELAY_BETWEEN_SENDS = float(args.delay_between_sends)
        if args.message_size:
            cls.MESSAGE_SIZE = int(args.message_size)

        return cls

    # ==============================================================
    # Directory Creation
    # ==============================================================
    @classmethod
    def create_required_dirs(cls):
        """Ensure essential directories exist."""
        for path in [
            cls.DATABASE_PATH,
            cls.MAILBOXES_DIR,
            cls.TEMP_EMAILS_DIR,
            cls.LOGS_DIR,
        ]:
            os.makedirs(path, exist_ok=True)

    # ==============================================================
    # Config Logging
    # ==============================================================
    @classmethod
    def log_config(cls):
        """Log all configuration values."""
        log_info_detailed("=== Application Configuration ===")

        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                value = getattr(cls, attr)
                log_info_detailed(f"{attr}: {value}")

        log_info_detailed("=================================")
