from typing import List, Optional
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QMessageBox,
    QStatusBar,
)

from src.client.frontend.controllers.app_controller_rich import AppController, ViewInterface
from src.client.frontend.gui_qt.compose_dialog_qt import ComposeDialog
from src.client.frontend.gui_qt.message_view_qt import render_html_to_text
from src.client.frontend.models.email_data import EmailData
from src.common.logger import get_class_logger


class MainWindowQt(QMainWindow, ViewInterface):
    """PySide6-based UI for the email client."""

    def __init__(self, username: str, password: str):
        super().__init__()
        self.setWindowTitle("Email Client")
        self.resize(1000, 640)

        self.log = get_class_logger(self)
        self.emails: List[EmailData] = []
        self.selected_email_index: Optional[int] = None

        # --- UI Setup ----------------------------------------------------------
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        # Header
        header = self._build_header(root_layout)
        root_layout.addLayout(header)

        # Main area
        main_area = QHBoxLayout()
        root_layout.addLayout(main_area, stretch=1)

        # Email list widget
        self.email_list = QListWidget()
        self.email_list.itemSelectionChanged.connect(self._on_select)
        main_area.addWidget(self.email_list, stretch=1)

        # Body widget
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        main_area.addWidget(self.body, stretch=2)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.show_status_message("Ready")

        # --- Controller Initialization (MUST BE LAST) --------------------------
        self.controller = AppController(self, username, password)

        # Safe to load now because email_list exists
        self.controller.load_user_emails(self.controller.user)

    def _build_header(self, parent_layout):
        layout = QHBoxLayout()

        self.compose_btn = QPushButton("Compose")
        self.compose_btn.clicked.connect(self.open_compose_window)
        layout.addWidget(self.compose_btn)

        self.reply_btn = QPushButton("Reply")
        self.reply_btn.clicked.connect(self._on_reply)
        layout.addWidget(self.reply_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.controller.refresh_emails)
        layout.addWidget(self.refresh_btn)

        layout.addStretch(1)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        layout.addWidget(self.logout_btn)

        return layout

    # ===== ViewInterface methods =====
    def display_emails(self, emails: List[EmailData]):
        self.emails = emails
        self.email_list.clear()
        for i, email in enumerate(emails, start=1):
            item = QListWidgetItem(f"{i}. {email.sender} — {email.subject}")
            self.email_list.addItem(item)

        if self.selected_email_index is None or self.selected_email_index >= len(emails):
            self.selected_email_index = None
            self.clear_email_content()
        else:
            self.email_list.setCurrentRow(self.selected_email_index)

    def display_email_content(self, html_content: str):
        self.body.setPlainText(render_html_to_text(html_content))

    def show_status_message(self, message: str):
        self.status_bar.showMessage(message)

    def open_compose_window(self, initial_data: Optional[dict] = None):
        dialog = ComposeDialog(self, initial_data or {})
        data = dialog.get_data()
        if data:
            self.controller.send_email(data)

    def clear_email_content(self):
        self.body.clear()

    def enable_refresh_button(self, enabled: bool):
        self.refresh_btn.setEnabled(enabled)

    def logout(self):
        self.controller.logout()
        self.close()

    def run_on_ui_thread(self, func, *args, **kwargs):
        QTimer.singleShot(0, lambda: func(*args, **kwargs))

    # ===== Internal callbacks =====
    def _on_select(self):
        rows = self.email_list.selectedIndexes()
        if not rows:
            return
        self.selected_email_index = rows[0].row()
        self.controller.select_email(self.selected_email_index)

    def _on_reply(self):
        if self.selected_email_index is None:
            QMessageBox.information(self, "Reply", "Select an email first.")
            return
        self.controller.reply_to_email(self.selected_email_index)

    def _on_delete(self):
        if self.selected_email_index is None:
            QMessageBox.information(self, "Delete", "Select an email first.")
            return
        confirm = QMessageBox.question(self, "Delete", "Delete this email?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.controller.delete_email(self.selected_email_index)
