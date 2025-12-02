import os
from typing import Dict, Any
from src.config import Config
from src.common.logger import get_class_logger


class User:
    """
    Represents a system user.
    Stores username and raw password (both required strings).
    """

    def __init__(self, username: str, password: str = "__internal__"):
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must be a non-empty string")
        if not isinstance(password, str):
            raise ValueError("password must be a string")

        self.log = get_class_logger(self)
        self.username = username.lower()
        self.password = password
        self.mailbox_path = os.path.join(Config.MAILBOXES_DIR, self.username)

        self.log.debug(f"User object initialized for {self.username}")
        self.log.info(self.to_string())

    # ---------------------------------------------------------
    # Password handling (still raw)
    # ---------------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        if not isinstance(raw_password, str) or not raw_password.strip():
            raise ValueError("Password must be a non-empty string.")
        self.log.debug(f"Setting password for {self.username}")
        self.password = raw_password
        self.log.info(f"Password for user {self.username} has been saved (raw).")

    def verify_password(self, raw_password: str) -> bool:
        verified = self.password == raw_password
        if verified:
            self.log.debug(f"Password verification successful for {self.username}")
        else:
            self.log.warning(f"Password verification failed for {self.username}")
        return verified

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> Dict[str, str]:
        """Serializes user data for JSON storage."""
        self.log.debug(f"Serializing user {self.username} to dict.")
        return {
            "username": self.username,
            "password": self.password,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Deserializes user data from JSON storage with strict type enforcement."""

        username = data.get("username")
        password = data.get("password")

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Invalid user record: 'username' must be a non-empty string.")

        if not isinstance(password, str) or not password.strip():
            raise ValueError("Invalid user record: 'password' must be a non-empty string.")

        return cls(username, password)

    def to_string(self) -> str:
        """
        Human-readable representation of a User object.
        Shows username, mailbox path, and password characteristics
        (but NEVER prints the raw password).
        """

        props = {
            "Username": self.username,
            "Mailbox Path": self.mailbox_path,
            "Password Set": self.password != "__internal__",
            "Password Length": len(self.password) if self.password else 0,
            "Object ID": hex(id(self)),
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nUser Object State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))

        return "\n".join(lines)
