from PySide6.QtCore import QObject, Slot, QModelIndex, Qt, QThread, Signal
from PySide6.QtWidgets import QDialog

from src.client.frontend.wrappers import StorageWrapper, SMTPWrapper, POP3Wrapper
from src.client.frontend.models import EmailListModel, EmailData
from src.client.frontend.views import ComposeWindow, SettingsDialog
from typing import Optional


class EmailFetcher(QThread):
    """Worker thread for fetching emails."""

    new_emails = Signal(list)
    finished = Signal()

    def __init__(self, pop3_wrapper, user, password):
        super().__init__()
        self.pop3 = pop3_wrapper
        self.user = user
        self.password = password

    def run(self):
        """Fetch emails in the background."""
        emails = self.pop3.fetch_new_emails(self.user, self.password)
        self.new_emails.emit(emails)
        self.finished.emit()


class AppController(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.storage = StorageWrapper()
        self.smtp = SMTPWrapper()
        self.pop3 = POP3Wrapper()
        self.user = "user1"  # Hardcoded for now
        self.password = "password"  # Hardcoded for now

        # Set up the model
        self.email_model = EmailListModel()
        self.main_window.email_list_view.setModel(self.email_model)

        # Connect signals
        self.main_window.email_list_view.clicked.connect(self.on_email_selected)
        self.main_window.compose_button.clicked.connect(self.on_compose_button_clicked)
        self.main_window.reply_button.clicked.connect(self.on_reply_clicked)
        self.main_window.reply_all_button.clicked.connect(self.on_reply_all_clicked)
        self.main_window.delete_button.clicked.connect(self.on_delete_clicked)
        self.main_window.settings_button.clicked.connect(self.on_settings_clicked)
        self.main_window.refresh_button.clicked.connect(self.on_refresh_clicked)

        # Initial load
        self.load_user_emails(self.user)

    def _get_current_selected_email(self) -> Optional[EmailData]:
        """Returns the currently selected EmailData object, or None."""
        indexes = self.main_window.email_list_view.selectedIndexes()
        if not indexes:
            return None
        return self.email_model.data(indexes[0], Qt.UserRole)

    def load_user_emails(self, user: str):
        """Loads emails for a user and updates the model."""
        emails = self.storage.list_emails(user)
        self.email_model.update_emails(emails)
        self.main_window.statusBar().showMessage(
            f"{len(emails)} emails loaded for {user}."
        )

    @Slot(QModelIndex)
    def on_email_selected(self, index: QModelIndex):
        """Handles the selection of an email in the list view."""
        if not index.isValid():
            return

        email_data = self.email_model.data(index, Qt.UserRole)
        if email_data:
            html_content = email_data.body_html or f"<pre>{email_data.body_text}</pre>"
            self.main_window.message_view.setHtml(html_content)
            self.main_window.statusBar().showMessage(
                f"Viewing email: {email_data.subject}"
            )

    @Slot()
    def on_compose_button_clicked(self, initial_data: Optional[dict] = None):
        """Opens the email composition window."""
        compose_window = ComposeWindow(self.main_window, initial_data=initial_data)
        compose_window.send_request.connect(self.on_send_email)
        compose_window.exec()

    @Slot()
    def on_reply_clicked(self):
        """Handles the reply action."""
        email = self._get_current_selected_email()
        if not email:
            self.main_window.statusBar().showMessage(
                "Please select an email to reply to.", 3000
            )
            return

        subject = f"Re: {email.subject}"
        body = f"\n\n--- On {email.date}, {email.sender} wrote: ---\n> "
        body += (email.body_text or "").replace("\n", "\n> ")

        initial_data = {
            "recipient": email.sender,
            "subject": subject,
            "body": body,
        }
        self.on_compose_button_clicked(initial_data)

    @Slot()
    def on_reply_all_clicked(self):
        """Handles the reply-all action (placeholder)."""
        email = self._get_current_selected_email()
        if not email:
            self.main_window.statusBar().showMessage(
                "Please select an email to reply to.", 3000
            )
            return
        self.main_window.statusBar().showMessage(
            "Reply All is not implemented yet.", 3000
        )

    @Slot()
    def on_delete_clicked(self):
        """Moves the selected email to the trash."""
        email = self._get_current_selected_email()
        if not email:
            self.main_window.statusBar().showMessage(
                "Please select an email to delete.", 3000
            )
            return

        was_deleted = self.storage.delete_email(self.user, email.uid)
        if was_deleted:
            self.main_window.statusBar().showMessage(
                f"Email '{email.subject}' moved to trash.", 3000
            )
            self.load_user_emails(self.user)  # Refresh the list
            self.main_window.message_view.setHtml("")  # Clear the view
        else:
            self.main_window.statusBar().showMessage(f"Error deleting email.", 3000)

    @Slot()
    def on_settings_clicked(self):
        """Opens the settings dialog."""
        current_settings = {"user": self.user, "password": self.password}
        dialog = SettingsDialog(self.main_window, settings=current_settings)
        if dialog.exec() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.user = new_settings.get("user", self.user)
            self.password = new_settings.get("password", self.password)
            self.main_window.statusBar().showMessage("Settings saved.", 3000)
            # Reload emails for the new user if it changed
            if self.user != current_settings["user"]:
                self.load_user_emails(self.user)

    @Slot(dict)
    def on_send_email(self, email_data: dict):
        """
        Handles the request to send an email.
        This should run in a background thread in a real app.
        """
        self.main_window.statusBar().showMessage("Sending email...")
        success = self.smtp.send_email(
            sender=f"{self.user}@localhost",
            recipients=[email_data["recipient"]],
            subject=email_data["subject"],
            body=email_data["body"],
        )
        if success:
            self.main_window.statusBar().showMessage("Email sent successfully!", 5000)
        else:
            self.main_window.statusBar().showMessage("Failed to send email.", 5000)

    @Slot()
    def on_refresh_clicked(self):
        """Fetches new emails from the POP3 server in a background thread."""
        self.main_window.statusBar().showMessage("Fetching new emails...")
        self.main_window.refresh_button.setEnabled(False)

        self.fetcher_thread = EmailFetcher(self.pop3, self.user, self.password)
        self.fetcher_thread.new_emails.connect(self.on_new_emails_received)
        self.fetcher_thread.finished.connect(self.on_fetching_finished)
        self.fetcher_thread.start()

    @Slot(list)
    def on_new_emails_received(self, new_emails: list):
        """Saves new emails to storage and reloads the inbox."""
        if not new_emails:
            self.main_window.statusBar().showMessage("No new emails.", 5000)
            return

        for email_content in new_emails:
            self.storage.save_email(self.user, email_content)

        self.main_window.statusBar().showMessage(
            f"Fetched {len(new_emails)} new email(s).", 5000
        )
        self.load_user_emails(self.user)

    @Slot()
    def on_fetching_finished(self):
        """Re-enables the refresh button once fetching is complete."""
        self.main_window.refresh_button.setEnabled(True)
