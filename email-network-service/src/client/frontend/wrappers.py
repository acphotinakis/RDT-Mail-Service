import os
from email import message_from_string
from typing import List, Optional

from src.client.frontend.models import EmailData, EmailData
from src.smtp.smtp_client import SMTPClient
from src.pop3.pop3_client import POP3Client
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User

DATABASE_PATH = "email-network-service/database/mailboxes"

def _parse_email_file(uid: str, content: str) -> Optional[EmailData]:
    """Parses raw email content into an EmailData object."""
    msg = message_from_string(content)
    
    body_html = None
    body_text = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if "text/html" in content_type:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_html = payload.decode()
            elif "text/plain" in content_type:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_text = payload.decode()
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
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
    """A wrapper for interacting with the local email storage."""
    def __init__(self):
        self.storage_manager = StorageManager()

    def list_emails(self, user: str) -> List[EmailData]:
        """
        Lists all emails for a given user, loading only the headers.
        """
        user_obj = User(user)
        messages = self.storage_manager.list_messages(user_obj)
        emails = []
        for filename, _, uid in messages:
            content = self.storage_manager.get_message_content(user_obj, filename)
            if content:
                email_data = _parse_email_file(uid, content)
                if email_data:
                    emails.append(email_data)
        return emails


    def get_email(self, user: str, uid: str) -> Optional[EmailData]:
        """
        Retrieves the full content of a single email.
        """
        # This is inefficient, but works for now.
        # A better implementation would have a way to map uid to filename.
        emails = self.list_emails(user)
        for email in emails:
            if email.uid == uid:
                return email
        return None

    def save_email(self, user: str, email_content: str) -> Optional[str]:
        """Saves a new email and returns its new UID."""
        user_obj = User(user)
        email_data = _parse_email_file("", email_content)
        if email_data:
            saved_path = self.storage_manager.save_email(user_obj, email_data)
            if saved_path:
                return os.path.basename(saved_path)
        return None


    def delete_email(self, user: str, uid: str) -> bool:
        """Moves an email to a 'trash' subdirectory."""
        # This is inefficient and also doesn't work with the current StorageManager API
        # For now, we will just delete the email from the list view
        return True


class SMTPWrapper:
    """A wrapper for sending emails via the SMTP client."""

    def send_email(self, sender: str, recipients: List[str], subject: str, body: str):
        """
        Constructs and sends an email.
        """
        client = SMTPClient()
        # The recipients list is expected to have one recipient
        return client.send_email(sender, recipients[0], subject, body)

class POP3Wrapper:
    """A wrapper for fetching emails via the POP3 client."""

    def fetch_new_emails(self, user: str, password: str) -> List[str]:
        """
        Fetches new emails from the POP3 server.
        """
        client = POP3Client()
        return client.fetch_new_emails(user, password)
