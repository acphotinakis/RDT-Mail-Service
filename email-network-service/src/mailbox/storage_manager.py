# Path: src/mailbox/storage_manager.py

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
    _instance = None
    _lock = threading.RLock()  # Global lock for singleton creation only

    def __new__(cls):
        """
        Singleton factory. Ensures only one StorageManager exists.
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
        """Initializes the manager."""

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
        Retrieves or creates a per-user lock.
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
        Thread-safe facade for saving an email (used by SMTP server).

        Steps:
            - Acquire user lock
            - Delegate to MailboxWriter.write_email()
            - Release lock
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
        Returns list of tuples: (filename, size_bytes, uid)

        Delegates to MailboxReader.list_messages()
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
        Returns the full raw content of a specific message.

        Delegates to MailboxReader.read_message()
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
        Retrieves the UID for a specific message.

        Delegates to MailboxReader.get_uid()
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
        Marks an email for deletion.

        Delegates to MailboxWriter.mark_message_as_deleted()
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
        Returns a diagnostic overview of the StorageManager including
        subsystem status and lock statistics.
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
