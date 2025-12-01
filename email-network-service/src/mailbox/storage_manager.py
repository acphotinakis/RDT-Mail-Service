# Path: src/mailbox/storage_manager.py

import os
import json
from typing import Dict, Optional, Tuple, List

from src.auth.user import User
from src.config import Config
from src.common.logger import get_class_logger

from src.mailbox.mailbox_reader import MailboxReader
from src.mailbox.mailbox_writer import MailboxWriter

import threading
from src.client.frontend.models import EmailData


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
        self.log = get_class_logger(self)
        self.log.info("StorageManager initialized.")

        self.mailbox_reader = MailboxReader()
        self.mailbox_writer = MailboxWriter()

        # Per-user locks
        self.locks: Dict[str, threading.Lock] = {}

    # ----------------------------------------------------------------------
    # Internal lock retrieval helper
    # ----------------------------------------------------------------------
    def get_lock(self, username: str) -> threading.Lock:
        """
        Retrieves or creates a per-user lock.
        """
        username = username.lower()
        if username not in self.locks:
            self.log.debug(f"Creating new mailbox lock for user '{username}'.")
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

        self.log.debug(f"[SAVE] Request to save email for user '{username}'.")

        with lock:
            self.log.debug(f"[SAVE] Lock acquired for '{username}'. Delegating to writer...")

            try:
                saved_path = self.mailbox_writer.write_email(user, email_data)
                if saved_path:
                    self.log.info(
                        f"[SAVE] Email successfully saved for '{username}'. Path: {saved_path}"
                    )
                else:
                    self.log.error(
                        f"[SAVE] Writer returned None — email save failed for '{username}'."
                    )
                return saved_path

            except Exception as e:
                self.log.error(
                    f"[SAVE] Exception occurred while writing email for '{username}': {e}",
                    exc_info=True,
                )
                return None

            finally:
                self.log.debug(f"[SAVE] Lock released for '{username}'.")

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

        self.log.debug(f"[LIST] Listing messages for '{username}'.")

        with lock:
            self.log.debug(f"[LIST] Lock acquired for '{username}'. Reading metadata...")

            try:
                entries = self.mailbox_reader.list_messages(user)
                self.log.debug(
                    f"[LIST] Retrieved {len(entries)} entries from metadata.json for '{username}'."
                )
                return entries

            except Exception as e:
                self.log.error(
                    f"[LIST] Error while listing messages for '{username}': {e}",
                    exc_info=True,
                )
                return []

            finally:
                self.log.debug(f"[LIST] Lock released for '{username}'.")

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

        self.log.debug(f"[GET] Request to retrieve message '{filename}' for user '{username}'.")

        with lock:
            self.log.debug(f"[GET] Lock acquired for '{username}'. Reading message file...")

            try:
                contents = self.mailbox_reader.read_message(user, filename)
                if contents is None:
                    self.log.warning(f"[GET] Message '{filename}' not found for '{username}'.")
                else:
                    self.log.debug(
                        f"[GET] Successfully loaded message '{filename}' ({len(contents)} chars)."
                    )
                return contents

            except Exception as e:
                self.log.error(
                    f"[GET] Error while reading message '{filename}' for '{username}': {e}",
                    exc_info=True,
                )
                return None

            finally:
                self.log.debug(f"[GET] Lock released for '{username}'.")

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

        self.log.debug(f"[UID] Request to load UID for '{filename}' (user: '{username}').")

        with lock:
            self.log.debug(f"[UID] Lock acquired for '{username}'. Looking up UID...")

            try:
                uid = self.mailbox_reader.get_uid(user, filename)
                if uid:
                    self.log.debug(f"[UID] UID for '{filename}' is '{uid}'.")
                else:
                    self.log.warning(f"[UID] No UID found for '{filename}' in metadata.json.")
                return uid

            except Exception as e:
                self.log.error(
                    f"[UID] Error while retrieving UID for '{filename}' (user '{username}'): {e}",
                    exc_info=True,
                )
                return None

            finally:
                self.log.debug(f"[UID] Lock released for '{username}'.")

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

        self.log.debug(
            f"[DELETE] Request to mark message '{filename}' as deleted for user '{username}'."
        )

        with lock:
            self.log.debug(
                f"[DELETE] Lock acquired for '{username}'. Marking message as deleted..."
            )

            try:
                success = self.mailbox_writer.mark_message_as_deleted(user, filename)
                if success:
                    self.log.debug(f"[DELETE] Successfully marked '{filename}' as deleted.")
                else:
                    self.log.warning(f"[DELETE] Failed to mark '{filename}' as deleted.")
                return success

            except Exception as e:
                self.log.error(
                    f"[DELETE] Error while marking message '{filename}' as deleted for '{username}': {e}",
                    exc_info=True,
                )
                return False

            finally:
                self.log.debug(f"[DELETE] Lock released for '{username}'.")
