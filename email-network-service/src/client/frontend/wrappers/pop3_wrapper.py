from typing import List
from src.pop3.pop3_client import POP3Client


class POP3Wrapper:
    def fetch_new_emails(self, user: str, password: str) -> List[str]:
        client = POP3Client()
        return client.fetch_new_emails(user, password)
