import os
from email import message_from_string
from email.message import Message
from typing import List, Optional

from src.client.frontend.models import EmailData

# Assuming smtp_client exists and has a certain API
# from src.smtp.smtp_client import SMTPClient 

# Assuming pop3_client exists and has a certain API
# from src.pop3.pop3_client import POP3Client

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

    def list_emails(self, user: str) -> List[EmailData]:
        """
        Lists all emails for a given user, loading only the headers.
        """
        user_mailbox_path = os.path.join(DATABASE_PATH, user)
        if not os.path.exists(user_mailbox_path):
            return []

        emails = []
        for filename in sorted(os.listdir(user_mailbox_path)):
            if filename.endswith(".txt"):
                uid = filename.removesuffix(".txt")
                filepath = os.path.join(user_mailbox_path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    email_data = _parse_email_file(uid, content)
                    if email_data:
                        emails.append(email_data)
        return emails

    def get_email(self, user: str, uid: str) -> Optional[EmailData]:
        """
        Retrieves the full content of a single email.
        """
        filepath = os.path.join(DATABASE_PATH, user, f"{uid}.txt")
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return _parse_email_file(uid, content)

    def save_email(self, user: str, email_content: str) -> Optional[str]:
        """Saves a new email and returns its new UID."""
        user_mailbox_path = os.path.join(DATABASE_PATH, user)
        os.makedirs(user_mailbox_path, exist_ok=True)
        
        # Find the next available email number
        existing_files = [f for f in os.listdir(user_mailbox_path) if f.startswith("email_") and f.endswith(".txt")]
        next_id = len(existing_files) + 1
        new_uid = f"email_{next_id:04d}"
        
        filepath = os.path.join(user_mailbox_path, f"{new_uid}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(email_content)
        
        return new_uid

    def delete_email(self, user: str, uid: str) -> bool:
        """Moves an email to a 'trash' subdirectory."""
        user_mailbox_path = os.path.join(DATABASE_PATH, user)
        trash_path = os.path.join(user_mailbox_path, "trash")
        os.makedirs(trash_path, exist_ok=True)

        source_path = os.path.join(user_mailbox_path, f"{uid}.txt")
        dest_path = os.path.join(trash_path, f"{uid}.txt")

        if os.path.exists(source_path):
            os.rename(source_path, dest_path)
            print(f"Moved {uid} to trash.")
            return True
        return False

class SMTPWrapper:
    """A wrapper for sending emails via the SMTP client."""

    def send_email(self, sender: str, recipients: List[str], subject: str, body: str):
        """
        Constructs and sends an email.
        NOTE: This is a placeholder implementation.
        """
        print("--- SENDING EMAIL ---")
        print(f"From: {sender}")
        print(f"To: {recipients}")
        print(f"Subject: {subject}")
        print("---")
        print(body)
        print("---------------------")
        return True

class POP3Wrapper:
    """A wrapper for fetching emails via the POP3 client."""

    def fetch_new_emails(self, user: str, password: str) -> List[str]:
        """
        Fetches new emails from the POP3 server.
        NOTE: This is a placeholder implementation. It will return a dummy email.
        """
        print(f"--- FETCHING EMAILS for {user} ---")
        # In a real implementation:
        # client = POP3Client(host, port)
        # client.authenticate(user, password)
        # new_messages = client.list_new_messages()
        # for msg_id in new_messages:
        #     content = client.retrieve(msg_id)
        #     yield content
        #     client.delete(msg_id)
        # client.close()

        # Placeholder dummy email
        dummy_email = (
            "From: dummy_sender@example.com\n"
            "To: user1@localhost\n"
            "Subject: This is a new email from the server\n"
            "Date: Tue, 25 Nov 2025 14:00:00 -0500\n\n"
            "This is the body of a new email fetched from the POP3 server."
        )
        print("--- FETCH COMPLETE ---")
        return [dummy_email]
