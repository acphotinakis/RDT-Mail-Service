import os
import json
import threading
import bcrypt
from typing import Optional, Dict
from src.common.config import USER_DB_FILE, MAILBOXES_DIR
from src.common.logger import get_class_logger


class User:
    """
    Represents a system user. Encapsulates username, hashed credentials,
    and the location of their mailbox storage.
    """

    def __init__(self, username: str, password_hash: Optional[bytes] = None):
        """
        Initialize a User object.
        Args:
            username: The unique username (will be lowercased).
            password_hash: The bcrypt hash of the password (bytes), if loading existing user.
        """
        self.username = username.lower()
        # Store hash as bytes internally for bcrypt compatibility
        self.password_hash = password_hash
        # Pre-calculate mailbox path based on project structure: database/mailboxes/{username}
        self.mailbox_path = os.path.join(MAILBOXES_DIR, self.username)

    def set_password(self, raw_password: str):
        """Hashes and sets the user's password using bcrypt with an automatic salt."""
        # bcrypt.hashpw requires bytes input for password and generates its own salt
        hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
        self.password_hash = hashed

    def verify_password(self, raw_password: str) -> bool:
        """Checks a raw password against the stored secure hash."""
        if not self.password_hash:
            return False
        # bcrypt.checkpw safely compares the raw input against the stored hash
        return bcrypt.checkpw(raw_password.encode("utf-8"), self.password_hash)

    def to_dict(self) -> dict:
        """Serializes user data for JSON storage."""
        return {
            "username": self.username,
            # Convert bytes hash to hex string for JSON compatibility
            "password_hash": self.password_hash.hex() if self.password_hash else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Deserializes user data from JSON storage."""
        username = data["username"]
        hash_str = data.get("password_hash")
        # Convert hex string back to bytes
        password_hash = bytes.fromhex(hash_str) if hash_str else None
        return cls(username, password_hash)
