from typing import List
from src.smtp.smtp_client import SMTPClient
from src.common.logger import *


class SMTPWrapper:
    def __init__(self):
        

    def send_email(self, sender: str, recipients: List[str], subject: str, body: str) -> bool:
        log_info_detailed(f"Preparing to send email from {sender} to {recipients}")
        all_sent = True
        for recipient in recipients:
            log_debug_detailed(f"Sending email to recipient: {recipient}")
            client = SMTPClient()
            try:
                success = client.send_email(sender, recipient, subject, body)
                if success:
                    log_info_detailed(f"Successfully sent email to {recipient}")
                else:
                    log_warning_detailed(f"Failed to send email to {recipient}")
                    all_sent = False
            except Exception as e:
                log_error_detailed(
                    f"Exception while sending email to {recipient}: {e}", exc_info=True
                )
                all_sent = False
        log_info_detailed(f"Finished sending emails. Overall success: {all_sent}")
        return all_sent
