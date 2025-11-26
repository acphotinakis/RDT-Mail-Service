# Path: src/mailbox/mailbox_writer.py
from src.auth.user import User
from src.client.frontend.models import EmailData
from src.common.config import MAILBOXES_DIR, TEMP_EMAILS_DIR
import os
import uuid
import time
from src.common.logger import get_class_logger


class MailboxWriter:
    def __init__(self):
        self.log = get_class_logger(self)
        self.log.info("Created MailboxWriter instance.")

    def write_email(self, user: User, email_data: EmailData):
        self.log.info(f"Writing email for user: {user.username}")

        # Final mailbox directory
        user_base_dir = os.path.join(MAILBOXES_DIR, user.username)
        os.makedirs(user_base_dir, exist_ok=True)

        # Temporary staging directory
        temp_user_dir = os.path.join(TEMP_EMAILS_DIR, user.username)
        os.makedirs(temp_user_dir, exist_ok=True)

        # Filename: timestamp + UUID
        unix_ts = int(time.time())
        filename = f"{unix_ts}_{uuid.uuid4()}.msg"

        temp_path = os.path.join(temp_user_dir, filename)
        final_path = os.path.join(user_base_dir, filename)

        self.log.debug(f"Temp write path: {temp_path}")
        self.log.debug(f"Final write path: {final_path}")

        # Convert raw MIME message to full RFC822 string
        try:
            raw_str = email_data.raw_message.as_string()
        except Exception as e:
            self.log.error(f"Failed to convert raw email to string: {e}")
            raise

        try:
            # Write the full MIME email to the temp file
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(raw_str)

            self.log.info("Email safely written to temp directory.")

            # Atomic move to final mailbox directory
            os.replace(temp_path, final_path)

            self.log.info("Email atomically moved to final mailbox directory.")

            return final_path

        except Exception as e:
            self.log.error(f"Failed during mailbox write: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
