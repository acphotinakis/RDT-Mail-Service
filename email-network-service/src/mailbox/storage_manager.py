"""
Thread-safe orchestration layer for mailbox persistence and retrieval.

The storage manager coordinates mailbox operations across SMTP and POP3
handlers while enforcing per-user locking. It maintains a singleton instance
that hands off work to reader and writer helpers and guarantees that mailbox
directories and metadata files remain consistent under concurrent access.
"""

import os
import json
from typing import Dict, Optional, Tuple, List

from src.auth.user import User
from src.config import Config
from src.common.logger import *

from src.mailbox.mailbox_reader import MailboxReader
from src.mailbox.mailbox_writer import MailboxWriter

import threading
from src.models.email_data import EmailData


class StorageManager:
    """
    Centralized, thread-safe controller for mailbox persistence.

    The storage manager is implemented as a singleton to ensure that a single
    coordinator enforces locking semantics for all mailbox interactions. It
    proxies read and write operations to dedicated helper classes while
    protecting per-user resources with granular locks so that concurrent SMTP
    and POP3 operations cannot corrupt metadata or message files.
    """

    _instance = None
    _lock = threading.RLock()  # Global lock for singleton creation only

    def __new__(cls):
        """
        Create or return the sole `StorageManager` instance.

        A re-entrant lock ensures that concurrent callers cannot race during
        instance creation. Subsequent calls return the previously constructed
        object without reinitializing shared state.

        Returns:
            StorageManager: The globally shared storage manager.
        """

        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StorageManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    # ----------------------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------------------
    def _initialize(self):
        """
        Initialize shared collaborators and per-user locks.

        This method is invoked once during singleton construction and sets up
        the mailbox reader and writer helpers along with the internal lock
        registry used to guard user-specific operations.
        """

        # Per-user locks
        self.locks: Dict[str, threading.Lock] = {}

        self.mailbox_reader = MailboxReader()
        self.mailbox_writer = MailboxWriter()

        log_info_detailed("StorageManager initialized.")
        log_info_detailed(self.to_string())

    # ----------------------------------------------------------------------
    # Internal lock retrieval helper
    # ----------------------------------------------------------------------
    def get_lock(self, username: str) -> threading.Lock:
        """
        Retrieve or lazily create the mutex protecting a user's mailbox.

        Args:
            username (str): The username whose mailbox operations must be
                synchronized.

        Returns:
            threading.Lock: The lock associated with the provided username.
        """
        username = username.lower()
        if username not in self.locks:
            log_debug_detailed(f"Creating new mailbox lock for user '{username}'.")
            self.locks[username] = threading.Lock()
        return self.locks[username]

    # ----------------------------------------------------------------------
    # 1. SAVE EMAIL (SMTP)
    # ----------------------------------------------------------------------
    def save_email(self, user: User, email_data: EmailData) -> Optional[str]:
        """
        Persist an email atomically for the provided user.

        The method acquires the per-user lock, delegates disk I/O to the
        `MailboxWriter`, and releases the lock regardless of success. Errors
        are logged and surfaced as a `None` return value.

        Args:
            user (User): The mailbox owner receiving the message.
            email_data (EmailData): Structured representation of the message
                to store.

        Returns:
            Optional[str]: Absolute path to the finalized message file when
            persistence succeeds; otherwise `None`.
        """
        username = user.username.lower()
        lock = self.get_lock(username)

        log_debug_detailed(f"[SAVE] Request to save email for user '{username}'.")

        with lock:
            log_debug_detailed(f"[SAVE] Lock acquired for '{username}'. Delegating to writer...")

            try:
                saved_path = self.mailbox_writer.write_email(user, email_data)
                if saved_path:
                    log_info_detailed(
                        f"[SAVE] Email successfully saved for '{username}'. Path: {saved_path}"
                    )
                else:
                    log_error_detailed(
                        f"[SAVE] Writer returned None — email save failed for '{username}'."
                    )
                return saved_path

            except Exception as e:
                log_error_detailed(
                    f"[SAVE] Exception occurred while writing email for '{username}': {e}",
                    exc_info=True,
                )
                return None

            finally:
                log_debug_detailed(f"[SAVE] Lock released for '{username}'.")

    # ----------------------------------------------------------------------
    # 2. LIST MESSAGES (POP3 - LIST, STAT, UIDL)
    # ----------------------------------------------------------------------
    def list_messages(self, user: User) -> List[Tuple[str, int, str]]:
        """
        Enumerate non-deleted messages for a user.

        The method returns the filename, size, and UID for each retained
        message by reading metadata under a per-user lock.

        Args:
            user (User): The account whose mailbox should be listed.

        Returns:
            List[Tuple[str, int, str]]: Sequence of `(filename, size_bytes, uid)`
            tuples for each visible message. Deleted messages are excluded.
        """
        username = user.username.lower()
        lock = self.get_lock(username)

        log_debug_detailed(f"[LIST] Listing messages for '{username}'.")

        with lock:
            log_debug_detailed(f"[LIST] Lock acquired for '{username}'. Reading metadata...")

            try:
                entries = self.mailbox_reader.list_messages(user)
                log_debug_detailed(
                    f"[LIST] Retrieved {len(entries)} entries from metadata.json for '{username}'."
                )
                return entries

            except Exception as e:
                log_error_detailed(
                    f"[LIST] Error while listing messages for '{username}': {e}",
                    exc_info=True,
                )
                return []

            finally:
                log_debug_detailed(f"[LIST] Lock released for '{username}'.")

    # ----------------------------------------------------------------------
    # 3. GET MESSAGE CONTENT (POP3 - RETR)
    # ----------------------------------------------------------------------
    def get_message_content(self, user: User, filename: str) -> Optional[str]:
        """
        Retrieve the raw contents of a stored message.

        The method acquires the user-level lock before delegating the read to
        the mailbox reader. Missing files or I/O failures are logged and
        surfaced as a `None` return value.

        Args:
            user (User): The mailbox owner.
            filename (str): The message filename to load.

        Returns:
            Optional[str]: Full message text when available; otherwise `None`.
        """
        username = user.username.lower()
        lock = self.get_lock(username)

        log_debug_detailed(f"[GET] Request to retrieve message '{filename}' for user '{username}'.")

        with lock:
            log_debug_detailed(f"[GET] Lock acquired for '{username}'. Reading message file...")

            try:
                contents = self.mailbox_reader.read_message(user, filename)
                if contents is None:
                    log_warning_detailed(f"[GET] Message '{filename}' not found for '{username}'.")
                else:
                    log_debug_detailed(
                        f"[GET] Successfully loaded message '{filename}' ({len(contents)} chars)."
                    )
                return contents

            except Exception as e:
                log_error_detailed(
                    f"[GET] Error while reading message '{filename}' for '{username}': {e}",
                    exc_info=True,
                )
                return None

            finally:
                log_debug_detailed(f"[GET] Lock released for '{username}'.")

    # ----------------------------------------------------------------------
    # 4. GET MESSAGE UID (POP3 - UIDL)
    # ----------------------------------------------------------------------
    def get_message_uid(self, user: User, filename: str) -> Optional[str]:
        """
        Look up the stable UID associated with a message file.

        Args:
            user (User): The mailbox owner.
            filename (str): The message filename whose UID is requested.

        Returns:
            Optional[str]: The UID string if present in metadata; otherwise
            `None`.
        """
        username = user.username.lower()
        lock = self.get_lock(username)

        log_debug_detailed(f"[UID] Request to load UID for '{filename}' (user: '{username}').")

        with lock:
            log_debug_detailed(f"[UID] Lock acquired for '{username}'. Looking up UID...")

            try:
                uid = self.mailbox_reader.get_uid(user, filename)
                if uid:
                    log_debug_detailed(f"[UID] UID for '{filename}' is '{uid}'.")
                else:
                    log_warning_detailed(f"[UID] No UID found for '{filename}' in metadata.json.")
                return uid

            except Exception as e:
                log_error_detailed(
                    f"[UID] Error while retrieving UID for '{filename}' (user '{username}'): {e}",
                    exc_info=True,
                )
                return None

            finally:
                log_debug_detailed(f"[UID] Lock released for '{username}'.")

    # ----------------------------------------------------------------------
    # 5. DELETE MESSAGE (POP3 - DELE)
    # ----------------------------------------------------------------------
    def delete_email(self, user: User, filename: str) -> bool:
        """
        Mark a message as deleted within metadata.

        The method does not remove the underlying file. It sets the deleted
        flag under a per-user lock so POP3 will exclude the message from
        listings.

        Args:
            user (User): The mailbox owner.
            filename (str): The message identifier to mark.

        Returns:
            bool: True if the deletion flag was recorded; otherwise False.
        """
        username = user.username.lower()
        lock = self.get_lock(username)

        log_debug_detailed(
            f"[DELETE] Request to mark message '{filename}' as deleted for user '{username}'."
        )

        with lock:
            log_debug_detailed(
                f"[DELETE] Lock acquired for '{username}'. Marking message as deleted..."
            )

            try:
                success = self.mailbox_writer.mark_message_as_deleted(user, filename)
                if success:
                    log_debug_detailed(f"[DELETE] Successfully marked '{filename}' as deleted.")
                else:
                    log_warning_detailed(f"[DELETE] Failed to mark '{filename}' as deleted.")
                return success

            except Exception as e:
                log_error_detailed(
                    f"[DELETE] Error while marking message '{filename}' as deleted for '{username}': {e}",
                    exc_info=True,
                )
                return False

            finally:
                log_debug_detailed(f"[DELETE] Lock released for '{username}'.")

    def to_string(self) -> str:
        """
        Produce a formatted diagnostic snapshot of manager state.

        Returns:
            str: Human-readable summary of collaborators and lock statistics.
        """
        props = {
            "Class": self.__class__.__name__,
            "MailboxReader": self.mailbox_reader.__class__.__name__,
            "MailboxWriter": self.mailbox_writer.__class__.__name__,
            "Users with Locks": len(self.locks),
            "Lock Keys": ", ".join(self.locks.keys()) if self.locks else "(none)",
            "Singleton Instance": hex(id(self)),
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nStorageManager State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
