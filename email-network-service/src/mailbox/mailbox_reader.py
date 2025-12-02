"""
Read-only accessors for mailbox contents and metadata.

The mailbox reader loads metadata, enumerates stored messages, retrieves
individual files, and exposes UID lookup helpers required by POP3 commands.
All operations are non-destructive and intended for concurrent read access.
"""

import os
import json
from typing import Dict, Optional, Tuple, List

from src.auth.user import User
from src.config import Config
from src.common.logger import *


class MailboxReader:
    """
    Provide read-only operations over a user's mailbox directory.

    The reader consumes metadata.json to support listing and UIDL semantics
    and exposes helpers for loading message bodies for POP3 RETR operations.
    """

    def __init__(self):
        """
        Initialize the mailbox reader and log its configuration.

        No filesystem operations occur during construction; the reader performs
        disk access only when individual methods are invoked.
        """

        log_info_detailed("MailboxReader initialized.")
        log_info_detailed(self.to_string())

    # Internal: Load metadata for a user
    def _load_metadata(self, metadata_path: str) -> Dict:
        """
        Load mailbox metadata with fallbacks for missing or invalid files.

        Args:
            metadata_path (str): Absolute path to the metadata.json file.

        Returns:
            Dict: Parsed metadata structure or a default empty mapping when the
            file cannot be read.
        """
        log_debug_detailed(f"Attempting to load metadata.json from: {metadata_path}")

        if not os.path.exists(metadata_path):
            log_warning_detailed(
                f"metadata.json not found at {metadata_path}. "
                "Returning empty metadata structure."
            )
            return {"messages": {}}

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            total_entries = len(metadata.get("messages", {}))
            log_debug_detailed(
                f"Successfully loaded metadata.json containing {total_entries} messages."
            )
            return metadata

        except Exception as e:
            log_error_detailed(
                f"Failed to load metadata.json at {metadata_path}.\n"
                f"Reason: {e}\n"
                "Returning empty metadata structure."
            )
            return {"messages": {}}

    # Public: List messages (POP3 LIST, STAT, UIDL)
    def list_messages(self, user: User) -> List[Tuple[str, int, str]]:
        """
        List visible messages for the given user.

        The listing excludes entries marked as deleted and provides filename,
        size, and UID tuples suitable for POP3 LIST, STAT, and UIDL responses.

        Args:
            user (User): Account whose mailbox is being inspected.

        Returns:
            List[Tuple[str, int, str]]: Tuples of `(filename, size_bytes, uid)`
            for each non-deleted message.
        """
        log_info_detailed(f"--- BEGIN MAILBOX LISTING transaction for user '{user.username}' ---")

        user_dir = os.path.join(Config.MAILBOXES_DIR, user.username)
        metadata_path = os.path.join(user_dir, "metadata.json")

        log_debug_detailed(f"Mailbox directory resolved: {user_dir}")
        log_debug_detailed(f"Metadata path resolved: {metadata_path}")

        metadata = self._load_metadata(metadata_path)
        messages = metadata.get("messages", {})

        listing = []
        total_size = 0

        for filename, meta in messages.items():
            uid = meta.get("uid")
            size_bytes = meta.get("size", 0)
            deleted = meta.get("deleted", False)

            if deleted:
                log_debug_detailed(f"Skipping message '{filename}' (marked deleted).")
                continue

            listing.append((filename, size_bytes, uid))
            total_size += size_bytes

            log_debug_detailed(
                f"Included message:\n"
                f"    filename: {filename}\n"
                f"    UID: {uid}\n"
                f"    size: {size_bytes} bytes"
            )

        log_info_detailed(
            f"Mailbox listing complete.\n"
            f"    Total visible messages: {len(listing)}\n"
            f"    Total size (bytes): {total_size}"
        )
        log_info_detailed(f"--- END MAILBOX LISTING transaction for user '{user.username}' ---")

        return listing

    # Public: Read full email (POP3 RETR)
    def read_message(self, user: User, filename: str) -> Optional[str]:
        """
        Load the raw contents of a stored message.

        Args:
            user (User): Owner of the mailbox.
            filename (str): Message filename to retrieve.

        Returns:
            Optional[str]: Message text when the file exists and can be read;
            otherwise `None`.
        """
        log_info_detailed(
            f"--- BEGIN READ MESSAGE for user '{user.username}' " f"(filename='{filename}') ---"
        )

        message_path = os.path.join(user.mailbox_path, filename)

        log_debug_detailed(f"Resolved message path: {message_path}")

        if not os.path.exists(message_path):
            log_error_detailed(f"Requested message file does not exist at: {message_path}")
            return None

        try:
            with open(message_path, "r", encoding="utf-8") as f:
                content = f.read()

            log_info_detailed(
                f"Successfully loaded {len(content)} bytes " f"from message file '{filename}'."
            )
            log_info_detailed(f"--- END READ MESSAGE for user '{user.username}' ---")
            return content

        except Exception as e:
            log_error_detailed(
                f"Failed to read message '{filename}' from disk.\n"
                f"Path: {message_path}\n"
                f"Reason: {e}"
            )
            return None

    # Public: Helper for POP3 UIDL

    def get_uid(self, user: User, filename: str) -> Optional[str]:
        """
        Retrieve the UID recorded for a specific message.

        Args:
            user (User): Owner of the mailbox.
            filename (str): Identifier of the message whose UID is requested.

        Returns:
            Optional[str]: UID value from metadata when present; otherwise
            `None`.
        """
        log_debug_detailed(f"Looking up UID for user '{user.username}', filename='{filename}'.")

        metadata_path = os.path.join(user.mailbox_path, "metadata.json")

        metadata = self._load_metadata(metadata_path)
        message_meta = metadata.get("messages", {}).get(filename)

        if not message_meta:
            log_error_detailed(f"Unable to find metadata entry for filename '{filename}'.")
            return None

        uid = message_meta.get("uid")
        log_debug_detailed(f"Retrieved UID '{uid}' for filename '{filename}'.")
        return uid

    def to_string(self) -> str:
        """
        Render a formatted diagnostic of reader configuration.

        Returns:
            str: Summary of mailbox paths used for read access.
        """
        props = {
            "Class": self.__class__.__name__,
            "Readable Mailbox Root": Config.MAILBOXES_DIR,
            "Temp Directory": Config.TEMP_EMAILS_DIR,
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nMailboxReader State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
