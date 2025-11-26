# Path: src/mailbox/mailbox_writer.py
from src.auth.user import User
from src.client.frontend.models import EmailData


USERNAME = "acphotinakis"
PASSWORD = "password123"


class MailboxWriter:
    def __init__(self, user: User, email_data: EmailData):
        self.user = user
        self.email_data = email_data

    def write_email(self):
        
