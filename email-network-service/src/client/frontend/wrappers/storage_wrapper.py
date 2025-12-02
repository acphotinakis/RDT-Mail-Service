import os
from typing import List, Optional
from email import message_from_string


from src.models.email_data import EmailData
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User
from src.common.logger import get_class_logger


log = get_class_logger("STORAGE_WRAPPER_QT")


def _parse_email_file(uid: str, content: str) -> Optional[EmailData]:
    log.debug(f"Parsing email file with UID: {uid if uid else 'Not specified'}")
    try:
        msg = message_from_string(content)
    except Exception as e:
        log.error(f"Failed to parse email content string: {e}", exc_info=True)
        return None

    body_html = None
    body_text = None

    if msg.is_multipart():
        log.debug("Email is multipart, walking through parts.")
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            # Skip attachments
            if "attachment" in cdispo:
                log.debug(f"Skipping attachment part with content type: {ctype}")
                continue

            try:
                payload = part.get_payload(decode=True)
            except Exception:
                log.warning("Could not decode part payload.", exc_info=True)
                continue

            if payload and isinstance(payload, bytes):
                charset = part.get_content_charset() or "utf-8"
                if ctype == "text/html":
                    body_html = payload.decode(charset, errors="replace")
                    log.debug(f"Extracted HTML body part ({len(body_html)} chars).")
                elif ctype == "text/plain":
                    body_text = payload.decode(charset, errors="replace")
                    log.debug(f"Extracted text body part ({len(body_text)} chars).")
    else:
        log.debug("Email is a single part.")
        try:
            payload = msg.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                charset = msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")
                log.debug(f"Extracted single part text body ({len(body_text)} chars).")
        except Exception:
            log.warning("Could not decode single part payload.", exc_info=True)

    email_data = EmailData(
        uid=uid,
        subject=msg.get("Subject", "No Subject"),
        sender=msg.get("From", "Unknown Sender"),
        recipient=msg.get("To", "Unknown Recipient"),
        date=msg.get("Date", ""),
        body_html=body_html,
        body_text=body_text,
        raw_message=msg,
    )
    log.debug(f"Successfully parsed email with subject: {email_data.subject}")
    return email_data


class StorageWrapper:
    def __init__(self):
        self.log = get_class_logger(self)
        self.storage_manager = StorageManager()
        self.log.info("StorageWrapper initialized.")

    def list_emails(self, user: str) -> List[EmailData]:
        self.log.info(f"Listing emails for user: {user}")
        user_obj = User(user)
        messages = self.storage_manager.list_messages(user_obj)
        emails = []
        self.log.debug(f"Found {len(messages)} messages in storage for user {user}.")

        for filename, _, uid in messages:
            self.log.debug(f"Reading content of message '{filename}' with UID '{uid}'.")
            content = self.storage_manager.get_message_content(user_obj, filename)
            if content:
                parsed = _parse_email_file(uid, content)
                if parsed:
                    emails.append(parsed)
            else:
                self.log.warning(f"Could not read content for message '{filename}'.")

        self.log.info(f"Listed {len(emails)} emails for user: {user}")
        return emails

    def save_email(self, user: str, content: str) -> Optional[str]:
        self.log.info(f"Saving new email for user: {user}")
        parsed = _parse_email_file("", content)
        if not parsed:
            self.log.error("Failed to parse email for saving.")
            return None

        user_obj = User(user)
        path = self.storage_manager.save_email(user_obj, parsed)
        if path:
            filename = os.path.basename(path)
            self.log.info(f"Email saved for user {user} with filename: {filename}")
            return filename
        else:
            self.log.error(f"Failed to save email for user {user}.")
            return None

    def delete_email(self, user: str, uid: str) -> bool:
        self.log.info(f"Attempting to delete email with UID: {uid} for user: {user}")
        user_obj = User(user)
        messages = self.storage_manager.list_messages(user_obj)

        filename_to_delete = None
        for filename, _, msg_uid in messages:
            if msg_uid == uid:
                filename_to_delete = filename
                self.log.debug(f"Found match: UID '{uid}' corresponds to filename '{filename}'.")
                break

        if filename_to_delete:
            self.log.debug(f"Calling storage manager to delete '{filename_to_delete}'.")
            deleted = self.storage_manager.delete_email(user_obj, filename_to_delete)
            if deleted:
                self.log.info(f"Successfully deleted email with UID: {uid}")
            else:
                self.log.error(f"Storage manager failed to delete email with UID: {uid}")
            return deleted
        else:
            self.log.warning(f"Could not find email with UID '{uid}' to delete.")
            return False
