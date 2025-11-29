from typing import List
from src.smtp.smtp_client import SMTPClient


class SMTPWrapper:
    def send_email(self, sender: str, recipients: List[str], subject: str, body: str) -> bool:
        all_sent = True
        for recipient in recipients:
            client = SMTPClient()
            success = client.send_email(sender, recipient, subject, body)
            if not success:
                all_sent = False
        return all_sent
