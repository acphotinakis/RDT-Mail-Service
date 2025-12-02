from typing import List
from src.pop3.pop3_client import POP3Client
from src.common.logger import *


class POP3Wrapper:
    def __init__(self):
        

    def fetch_new_emails(self, user: str, password: str) -> List[str]:
        log_info_detailed(f"Fetching new emails for user: {user}")
        client = POP3Client()
        try:
            emails = client.fetch_new_emails(user, password)
            log_info_detailed(f"Fetched {len(emails)} new emails for user: {user}")
            return emails
        except Exception as e:
            log_error_detailed(
                f"An error occurred while fetching emails for {user}: {e}", exc_info=True
            )
            return []
