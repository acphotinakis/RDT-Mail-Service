# Path: src/mailbox/mailbox_reader.py

import os
import json
from typing import Dict, Optional, Tuple, List

from src.auth.user import User
from src.config import MAILBOXES_DIR
from src.common.logger import get_class_logger


class MailboxReader:
    """
    Provides read-only access to a user's mailbox directory.
    Responsible for:
      - Efficient retrieval of metadata.json
      - Fast listing of messages (POP3 LIST, STAT, UIDL)
      - Loading full raw content of message files (POP3 RETR)
    """

    def __init__(self):
        self.log = get_class_logger(self)
        self.log.info("MailboxReader initialized.")

    # Internal: Load metadata for a user
    def _load_metadata(self, metadata_path: str) -> Dict:
        """
        Safely loads the user's metadata.json file.

        Returns empty structure if missing or corrupt.
        """
        self.log.debug(f"Attempting to load metadata.json from: {metadata_path}")

        if not os.path.exists(metadata_path):
            self.log.warning(
                f"metadata.json not found at {metadata_path}. "
                "Returning empty metadata structure."
            )
            return {"messages": {}}

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            total_entries = len(metadata.get("messages", {}))
            self.log.debug(
                f"Successfully loaded metadata.json containing {total_entries} messages."
            )
            return metadata

        except Exception as e:
            self.log.error(
                f"Failed to load metadata.json at {metadata_path}.\n"
                f"Reason: {e}\n"
                "Returning empty metadata structure."
            )
            return {"messages": {}}

    # Public: List messages (POP3 LIST, STAT, UIDL)
    def list_messages(self, user: User) -> List[Tuple[str, int, str]]:
        """
        Returns a list of tuples describing each message:
            (filename, size_bytes, uid)

        This enables:
            - LIST (size listing)
            - STAT (count & total size)
            - UIDL (UID listing)
        """
        self.log.info(f"--- BEGIN MAILBOX LISTING transaction for user '{user.username}' ---")

        user_dir = os.path.join(MAILBOXES_DIR, user.username)
        metadata_path = os.path.join(user_dir, "metadata.json")

        self.log.debug(f"Mailbox directory resolved: {user_dir}")
        self.log.debug(f"Metadata path resolved: {metadata_path}")

        metadata = self._load_metadata(metadata_path)
        messages = metadata.get("messages", {})

        listing = []
        total_size = 0

        for filename, meta in messages.items():
            uid = meta.get("uid")
            size_bytes = meta.get("size", 0)
            deleted = meta.get("deleted", False)

            if deleted:
                self.log.debug(f"Skipping message '{filename}' (marked deleted).")
                continue

            listing.append((filename, size_bytes, uid))
            total_size += size_bytes

            self.log.debug(
                f"Included message:\n"
                f"    filename: {filename}\n"
                f"    UID: {uid}\n"
                f"    size: {size_bytes} bytes"
            )

        self.log.info(
            f"Mailbox listing complete.\n"
            f"    Total visible messages: {len(listing)}\n"
            f"    Total size (bytes): {total_size}"
        )
        self.log.info(f"--- END MAILBOX LISTING transaction for user '{user.username}' ---")

        return listing

    # Public: Read full email (POP3 RETR)
    def read_message(self, user: User, filename: str) -> Optional[str]:
        """
        Loads and returns the raw content of a message file by filename.

        Used by POP3 RETR handler.
        """
        self.log.info(
            f"--- BEGIN READ MESSAGE for user '{user.username}' " f"(filename='{filename}') ---"
        )

        message_path = os.path.join(user.mailbox_path, filename)

        self.log.debug(f"Resolved message path: {message_path}")

        if not os.path.exists(message_path):
            self.log.error(f"Requested message file does not exist at: {message_path}")
            return None

        try:
            with open(message_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.log.info(
                f"Successfully loaded {len(content)} bytes " f"from message file '{filename}'."
            )
            self.log.info(f"--- END READ MESSAGE for user '{user.username}' ---")
            return content

        except Exception as e:
            self.log.error(
                f"Failed to read message '{filename}' from disk.\n"
                f"Path: {message_path}\n"
                f"Reason: {e}"
            )
            return None

    # Public: Helper for POP3 UIDL

    def get_uid(self, user: User, filename: str) -> Optional[str]:
        """
        Returns the UID associated with a message file.
        """
        self.log.debug(f"Looking up UID for user '{user.username}', filename='{filename}'.")

        metadata_path = os.path.join(user.mailbox_path, "metadata.json")

        metadata = self._load_metadata(metadata_path)
        message_meta = metadata.get("messages", {}).get(filename)

        if not message_meta:
            self.log.error(f"Unable to find metadata entry for filename '{filename}'.")
            return None

        uid = message_meta.get("uid")
        self.log.debug(f"Retrieved UID '{uid}' for filename '{filename}'.")
        return uid
