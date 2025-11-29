from typing import List
from src.pop3.pop3_client import POP3Client
from src.common.logger import get_class_logger


class POP3Wrapper:
    def __init__(self):
        self.log = get_class_logger(self)

    def fetch_new_emails(self, user: str, password: str) -> List[str]:
        self.log.info(f"Fetching new emails for user: {user}")
        client = POP3Client()
        try:
            emails = client.fetch_new_emails(user, password)
            self.log.info(f"Fetched {len(emails)} new emails for user: {user}")
            return emails
        except Exception as e:
            self.log.error(f"An error occurred while fetching emails for {user}: {e}", exc_info=True)
            return []
