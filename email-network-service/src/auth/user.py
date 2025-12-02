"""
Domain model representing an authenticated user and mailbox owner.

This module defines the `User` class, which encapsulates credential storage,
mailbox path resolution, and serialization helpers used by authentication and
mailbox subsystems.
"""

import os
from typing import Dict, Any
from src.config import Config
from src.common.logger import *


import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class User:
    """
    Represent an authenticated user and associated mailbox location.

    Instances track normalized usernames, raw passwords used by the simulation,
    and the filesystem path to the user's mailbox root.
    """

    def __init__(self, username: str, password: str = "__internal__"):
        """
        Initialize a user with validated credentials.

        Args:
            username (str): Identifier for the user; normalized to lowercase.
            password (str, optional): Raw password string. Defaults to the
                internal placeholder value.

        Raises:
            ValueError: If the username or password arguments are not
            well-formed strings.
        """
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must be a non-empty string")
        if not isinstance(password, str):
            raise ValueError("password must be a string")

        self.username = username.lower()
        self.password = password
        self.mailbox_path = os.path.join(Config.MAILBOXES_DIR, self.username)

        log_debug_detailed(f"User object initialized for {self.username}")
        log_info_detailed(self.to_string())

    # ---------------------------------------------------------
    # Password handling (still raw)
    # ---------------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        """
        Replace the stored password with a new value after validation.

        Args:
            raw_password (str): New password to associate with the user.

        Raises:
            ValueError: If the provided password is empty or not a string.
        """
        if not isinstance(raw_password, str) or not raw_password.strip():
            raise ValueError("Password must be a non-empty string.")
        log_debug_detailed(f"Setting password for {self.username}")
        self.password = raw_password
        log_info_detailed(f"Password for user {self.username} has been saved (raw).")

    def verify_password(self, raw_password: str) -> bool:
        """
        Compare the provided password with the stored value.

        Args:
            raw_password (str): Candidate password to check.

        Returns:
            bool: True when the provided password matches the stored value;
            otherwise False.
        """
        verified = self.password == raw_password
        if verified:
            log_debug_detailed(f"Password verification successful for {self.username}")
        else:
            log_warning_detailed(f"Password verification failed for {self.username}")
        return verified

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> Dict[str, str]:
        """
        Serialize user state for JSON persistence.

        Returns:
            Dict[str, str]: Mapping containing normalized username and raw
            password.
        """
        log_debug_detailed(f"Serializing user {self.username} to dict.")
        return {
            "username": self.username,
            "password": self.password,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """
        Reconstruct a `User` from a dictionary payload.

        Args:
            data (Dict[str, Any]): Mapping containing serialized user fields.

        Returns:
            User: New instance created from the provided data.

        Raises:
            ValueError: If required fields are missing or not valid strings.
        """

        username = data.get("username")
        password = data.get("password")

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Invalid user record: 'username' must be a non-empty string.")

        if not isinstance(password, str) or not password.strip():
            raise ValueError("Invalid user record: 'password' must be a non-empty string.")

        return cls(username, password)

    def _relative_path(self, path: str) -> str:
        """
        Convert an absolute path to one relative to the project root.

        Args:
            path (str): Filesystem path to relativize.

        Returns:
            str: Relative path when conversion succeeds; otherwise the original
            path.
        """
        try:
            return os.path.relpath(path, PROJECT_ROOT)
        except Exception:
            return path

    def to_string(self) -> str:
        """
        Produce a diagnostic representation of the user state.

        Returns:
            str: Multi-line summary that omits the raw password but reports
            mailbox path and metadata about credential presence.
        """
        relative_mailbox = self._relative_path(self.mailbox_path)

        props = {
            "Username": self.username,
            "Mailbox Path": relative_mailbox,
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
