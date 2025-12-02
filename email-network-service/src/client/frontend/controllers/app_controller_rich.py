import threading
from typing import Optional, List


from src.client.frontend.wrappers.storage_wrapper import StorageWrapper
from src.client.frontend.wrappers.smtp_wrapper import SMTPWrapper
from src.client.frontend.wrappers.pop3_wrapper import POP3Wrapper
from src.models.email_data import EmailData
import src.client.frontend.autologin_manager as autologin_manager
from src.common.logger import *

from src.common.logger import *


class ViewInterface:
    def display_emails(self, emails: List[EmailData]): ...
    def display_email_content(self, html_content: str): ...
    def show_status_message(self, message: str): ...
    def open_compose_window(self, initial_data: Optional[dict] = None): ...
    def clear_email_content(self): ...
    def enable_refresh_button(self, enabled: bool): ...
    def logout(self): ...
    def run_on_ui_thread(self, func, *args, **kwargs): ...


def fetch_emails_worker(pop3_wrapper, user, password, callback):
    log.info(f"Starting email fetch worker for user: {user}")
    emails = pop3_wrapper.fetch_new_emails(user, password)
    log.info(f"Email fetch worker finished. Found {len(emails)} new emails.")
    callback(emails)


class AppController:
    def __init__(self, view: ViewInterface, username: str, password: str):

        self.view = view
        self.storage = StorageWrapper()
        self.smtp = SMTPWrapper()
        self.pop3 = POP3Wrapper()

        # User is now dynamic, not hardcoded
        self.user = username
        self.password = password

        self.emails: List[EmailData] = []
        log_info_detailed(f"AppController initialized for user: {self.user}")

        self.load_user_emails(self.user)

    def load_user_emails(self, user: str):
        log_info_detailed(f"Loading emails for user: {user}")
        self.emails = self.storage.list_emails(user)
        self.view.display_emails(self.emails)
        self.view.show_status_message(f"{len(self.emails)} emails loaded.")
        log_info_detailed(f"Loaded {len(self.emails)} emails.")

    def select_email(self, index: int):
        if 0 <= index < len(self.emails):
            email = self.emails[index]
            log_info_detailed(f"Selected email at index {index}, subject: {email.subject}")
            html = email.body_html or f"<pre>{email.body_text}</pre>"
            self.view.display_email_content(html)
            self.view.show_status_message(f"Viewing: {email.subject}")

    def compose_email(self, initial_data: Optional[dict] = None):
        log_info_detailed("Opening compose window.")
        self.view.open_compose_window(initial_data)

    def reply_to_email(self, index: int):
        if not (0 <= index < len(self.emails)):
            log_warning_detailed(f"Reply attempt with invalid index: {index}")
            self.view.show_status_message("Select an email first.")
            return

        email = self.emails[index]
        log_info_detailed(f"Replying to email, subject: {email.subject}")
        quoted = (email.body_text or "").replace("\n", "\n> ")
        initial = {
            "recipient": email.sender,
            "subject": "Re: " + email.subject,
            "body": f"\n\n--- On {email.date}, {email.sender} wrote: ---\n> {quoted}",
        }
        self.compose_email(initial)

    def delete_email(self, index: int):
        if not (0 <= index < len(self.emails)):
            log_warning_detailed(f"Delete attempt with invalid index: {index}")
            return

        email = self.emails[index]
        log_info_detailed(f"Deleting email with UID: {email.uid}")
        deleted = self.storage.delete_email(self.user, email.uid)
        if deleted:
            log_info_detailed("Email deleted successfully from storage.")
            self.view.show_status_message("Email deleted.")
            self.load_user_emails(self.user)
            self.view.clear_email_content()
        else:
            log_error_detailed(f"Failed to delete email with UID: {email.uid}")
            self.view.show_status_message("Failed to delete email.")

    def send_email(self, email_data: dict):
        recipient = email_data.get("recipient", "N/A")
        log_info_detailed(f"Attempting to send email to: {recipient}")
        self.view.show_status_message("Sending email...")
        ok = self.smtp.send_email(
            sender=f"{self.user}@localhost",
            recipients=[email_data["recipient"]],
            subject=email_data["subject"],
            body=email_data["body"],
        )
        msg = "Email sent!" if ok else "Failed to send."
        self.view.show_status_message(msg)
        if ok:
            log_info_detailed(f"Email successfully sent to: {recipient}")
        else:
            log_error_detailed(f"Failed to send email to: {recipient}")

    def refresh_emails(self):
        log_info_detailed("Starting email refresh process.")
        self.view.show_status_message("Fetching new emails...")
        self.view.enable_refresh_button(False)

        thread = threading.Thread(
            target=fetch_emails_worker,
            args=(self.pop3, self.user, self.password, self._deliver_new_emails),
            name="fetch-emails-worker",
        )
        thread.start()

    def _deliver_new_emails(self, messages):
        """Ensure email updates are delivered on the UI thread when needed."""
        log_debug_detailed(f"Delivering {len(messages)} new messages to UI thread.")
        self.view.run_on_ui_thread(self.on_new_emails, messages)

    def on_new_emails(self, messages):
        log_info_detailed(f"Processing {len(messages)} new emails from fetch worker.")
        if not messages:
            self.view.show_status_message("No new emails.")
            self.view.enable_refresh_button(True)
            return

        for raw in messages:
            log_debug_detailed("Saving new raw message to storage.")
            self.storage.save_email(self.user, raw)

        self.view.show_status_message(f"Fetched {len(messages)} new email(s).")
        self.load_user_emails(self.user)
        self.view.enable_refresh_button(True)
        log_info_detailed("Finished processing new emails.")

    def open_settings(self):
        log_info_detailed("Settings opened (not implemented).")
        self.view.show_status_message("Settings not implemented.")

    def logout(self):
        log_info_detailed(f"User {self.user} logging out.")
        autologin_manager.delete_credentials()
        self.view.show_status_message("Logged out.")
        log_info_detailed("Logout process complete.")
