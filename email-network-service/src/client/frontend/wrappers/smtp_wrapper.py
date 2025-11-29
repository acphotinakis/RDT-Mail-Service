from typing import List
from src.smtp.smtp_client import SMTPClient
from src.common.logger import get_class_logger


class SMTPWrapper:
    def __init__(self):
        self.log = get_class_logger(self)

    def send_email(self, sender: str, recipients: List[str], subject: str, body: str) -> bool:
        self.log.info(f"Preparing to send email from {sender} to {recipients}")
        all_sent = True
        for recipient in recipients:
            self.log.debug(f"Sending email to recipient: {recipient}")
            client = SMTPClient()
            try:
                success = client.send_email(sender, recipient, subject, body)
                if success:
                    self.log.info(f"Successfully sent email to {recipient}")
                else:
                    self.log.warning(f"Failed to send email to {recipient}")
                    all_sent = False
            except Exception as e:
                self.log.error(f"Exception while sending email to {recipient}: {e}", exc_info=True)
                all_sent = False
        self.log.info(f"Finished sending emails. Overall success: {all_sent}")
        return all_sent
