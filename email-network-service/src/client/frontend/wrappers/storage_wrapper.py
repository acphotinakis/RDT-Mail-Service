import os
from typing import List, Optional
from email import message_from_string

from src.client.frontend.models.email_data import EmailData
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User


def _parse_email_file(uid: str, content: str) -> Optional[EmailData]:
    msg = message_from_string(content)

    body_html = None
    body_text = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)

            if payload and isinstance(payload, bytes):
                if ctype == "text/html":
                    body_html = payload.decode()
                elif ctype == "text/plain":
                    body_text = payload.decode()
    else:
        payload = msg.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
            body_text = payload.decode()

    return EmailData(
        uid=uid,
        subject=msg.get("Subject", "No Subject"),
        sender=msg.get("From", "Unknown Sender"),
        recipient=msg.get("To", "Unknown Recipient"),
        date=msg.get("Date", ""),
        body_html=body_html,
        body_text=body_text,
        raw_message=msg,
    )


class StorageWrapper:
    def __init__(self):
        self.storage_manager = StorageManager()

    def list_emails(self, user: str) -> List[EmailData]:
        user_obj = User(user)
        messages = self.storage_manager.list_messages(user_obj)
        emails = []

        for filename, _, uid in messages:
            content = self.storage_manager.get_message_content(user_obj, filename)
            if content:
                parsed = _parse_email_file(uid, content)
                if parsed:
                    emails.append(parsed)

        return emails

    def save_email(self, user: str, content: str) -> Optional[str]:
        parsed = _parse_email_file("", content)
        if not parsed:
            return None

        user_obj = User(user)
        path = self.storage_manager.save_email(user_obj, parsed)
        return os.path.basename(path) if path else None

    def delete_email(self, user: str, uid: str) -> bool:
        user_obj = User(user)
        messages = self.storage_manager.list_messages(user_obj)
        
        filename_to_delete = None
        for filename, _, msg_uid in messages:
            if msg_uid == uid:
                filename_to_delete = filename
                break
        
        if filename_to_delete:
            return self.storage_manager.delete_email(user_obj, filename_to_delete)
            
        return False
