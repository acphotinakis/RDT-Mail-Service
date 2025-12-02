# Path: src/mailbox/mailbox_writer.py

from src.auth.user import User
from src.models.email_data import EmailData
from src.config import Config
import os
import uuid
import time
import json
from src.common.logger import get_class_logger
from typing import Optional


class MailboxWriter:
    def __init__(self):
        self.log = get_class_logger(self)
        self.log.info("Initialized MailboxWriter.")
        self.log.info(self.to_string())

    # ------------------------------
    # Metadata Helpers
    # ------------------------------
    def _load_metadata(self, metadata_path: str) -> dict:
        self.log.debug(f"Attempting to load metadata from: {metadata_path}")

        if not os.path.exists(metadata_path):
            self.log.warning(
                f"No metadata.json found at {metadata_path}. "
                f"Creating a fresh metadata structure."
            )
            return {"messages": {}}

        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
                total = len(data.get("messages", {}))
                self.log.debug(f"Loaded existing metadata.json with {total} message entries.")
                return data
        except Exception as e:
            self.log.error(
                f"Failed to load metadata.json due to: {e}. " f"Reinitializing metadata structure."
            )
            return {"messages": {}}

    def _save_metadata(self, metadata_path: str, data: dict):
        temp_path = metadata_path + ".tmp"
        self.log.debug(f"Saving updated metadata to temp file: {temp_path}")

        try:
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=4)

            self.log.debug(
                f"Successfully wrote metadata temp file. "
                f"Now performing atomic replace -> {metadata_path}"
            )
            os.replace(temp_path, metadata_path)

            self.log.info(f"metadata.json updated successfully at: {metadata_path}")

        except Exception as e:
            self.log.error(
                f"Error writing metadata.json (temp: {temp_path}). "
                f"Reason: {e}. Metadata may be partially updated."
            )
            # DO NOT delete temp_path; leave for debugging

    # ------------------------------
    # Email Writer
    # ------------------------------

    def write_email(self, user: User, email_data: EmailData) -> Optional[str]:
        self.log.info(f"--- BEGIN EMAIL WRITE TRANSACTION for user '{user.username}' ---")

        # Establish user mailbox directories
        user_dir = os.path.join(Config.MAILBOXES_DIR, user.username)
        os.makedirs(user_dir, exist_ok=True)
        self.log.debug(f"Ensured mailbox directory exists: {user_dir}")

        temp_user_dir = os.path.join(Config.TEMP_EMAILS_DIR, user.username)
        os.makedirs(temp_user_dir, exist_ok=True)
        self.log.debug(f"Ensured TEMP mailbox directory exists: {temp_user_dir}")

        # Prepare metadata path
        metadata_path = os.path.join(user_dir, "metadata.json")
        self.log.debug(f"Using metadata.json path: {metadata_path}")

        # Generate filename
        unix_ts = int(time.time())
        uuid_part = uuid.uuid4()
        filename = f"{unix_ts}_{uuid_part}.msg"

        temp_path = os.path.join(temp_user_dir, filename)
        final_path = os.path.join(user_dir, filename)

        self.log.info(
            f"Assigned message filename: {filename}\n"
            # f"    Temp path:  {temp_path}\n"
            # f"    Final path: {final_path}"
        )

        # Extract MIME text:
        try:
            raw_email = email_data.raw_message.as_string()
            self.log.debug(
                f"Converted EmailData.raw_message into MIME text " f"({len(raw_email)} bytes)"
            )
        except Exception as e:
            self.log.error(
                f"Failed converting raw_message to string: {e}. " "Email will NOT be written."
            )
            return None

        # --------------------------------
        # Write email to TEMP file
        # --------------------------------
        self.log.debug(f"Writing MIME email content to TEMP file: {temp_path}")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(raw_email)
        except Exception as e:
            self.log.error(f"Failed to write temp email file '{temp_path}'. Reason: {e}")
            return None

        self.log.debug("TEMP email file write successful.")

        # --------------------------------
        # Atomic move → mailbox
        # --------------------------------
        self.log.debug(f"Attempting atomic os.replace from TEMP to final mailbox file.")
        try:
            os.replace(temp_path, final_path)
        except Exception as e:
            self.log.error(
                f"Atomic move failed: Could not replace TEMP file:\n"
                f"    from = {temp_path}\n"
                f"    to   = {final_path}\n"
                f"Reason: {e}"
            )
            return None

        self.log.info(f"Email file finalized at: {final_path}")

        # --------------------------------
        # Update metadata.json
        # --------------------------------
        metadata = self._load_metadata(metadata_path)

        # Determine stable UID
        stable_uid = email_data.uid or str(uuid.uuid4())
        self.log.debug(f"Assigned UID for message:\n" f"    UID: {stable_uid}")

        # Get file size for POP3 LIST response
        try:
            size_bytes = os.path.getsize(final_path)
            self.log.debug(f"Computed size of stored email: {size_bytes} bytes")
        except OSError as e:
            self.log.error(f"Failed to obtain file size for '{final_path}': {e}")
            size_bytes = 0

        # Add new metadata entry
        metadata_entry = {"uid": stable_uid, "size": size_bytes, "deleted": False}

        self.log.debug(
            "Adding metadata entry:\n"
            f"    filename: {filename}\n"
            f"    metadata: {metadata_entry}"
        )

        metadata["messages"][filename] = metadata_entry

        # Save metadata json
        self._save_metadata(metadata_path, metadata)

        self.log.info(f"Completed metadata update for new message: {filename}")
        self.log.info(f"--- END EMAIL WRITE TRANSACTION for user '{user.username}' ---")

        return final_path

    def mark_message_as_deleted(self, user: User, filename: str) -> bool:
        """
        Marks a message as deleted in the metadata.
        """
        self.log.info(f"--- BEGIN EMAIL DELETE TRANSACTION for user '{user.username}' ---")
        metadata_path = os.path.join(Config.MAILBOXES_DIR, user.username, "metadata.json")
        metadata = self._load_metadata(metadata_path)

        if filename in metadata["messages"]:
            metadata["messages"][filename]["deleted"] = True
            self._save_metadata(metadata_path, metadata)
            self.log.info(f"Marked message '{filename}' as deleted.")
            self.log.info(f"--- END EMAIL DELETE TRANSACTION for user '{user.username}' ---")
            return True
        else:
            self.log.warning(f"Message '{filename}' not found in metadata.")
            self.log.info(f"--- END EMAIL DELETE TRANSACTION for user '{user.username}' ---")
            return False

    def to_string(self) -> str:
        """
        Returns a diagnostic overview of the MailboxWriter state.
        """
        props = {
            "Class": self.__class__.__name__,
            "Logger Name": self.log.name,
            "Mailbox Root": Config.MAILBOXES_DIR,
            "Temp Root": Config.TEMP_EMAILS_DIR,
            "Supports Atomic Writes": True,
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nMailboxWriter State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
