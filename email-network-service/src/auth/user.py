import os
import json
import threading
from typing import Optional, Dict
from src.common.config import USER_DB_FILE, MAILBOXES_DIR
from src.common.logger import get_class_logger


class User:
    """
    Represents a system user.
    Stores username, raw password, and mailbox path.
    """

    def __init__(self, username: str, password: Optional[str] = None):
        self.log = get_class_logger(self)
        self.username = username.lower()
        self.password = password  # <-- Plain-text password stored directly
        self.mailbox_path = os.path.join(MAILBOXES_DIR, self.username)

        self.log.debug(f"User object initialized for {self.username}")

    # ---------------------------------------------------------
    # Password handling (plain text)
    # ---------------------------------------------------------

    def set_password(self, raw_password: str):
        """Stores the password directly (no hashing)."""
        self.log.debug(f"Setting password for {self.username}")
        self.password = raw_password
        self.log.info(f"Password for user {self.username} has been saved (raw).")

    def verify_password(self, raw_password: str) -> bool:
        """Checks raw password directly."""
        if self.password is None:
            self.log.warning(
                f"Password verification for {self.username} failed: no password saved."
            )
            return False

        result = self.password == raw_password
        if result:
            self.log.debug(f"Password verification for {self.username} successful.")
        else:
            self.log.warning(f"Password verification for {self.username} failed.")
        return result

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> dict:
        """Serializes user data for JSON storage."""
        self.log.debug(f"Serializing user {self.username} to dictionary.")
        return {
            "username": self.username,
            "password": self.password,  # <-- Plain text in JSON
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Deserializes user data from JSON storage."""
        username = data.get("username")
        password = data.get("password")
        return cls(username, password)
