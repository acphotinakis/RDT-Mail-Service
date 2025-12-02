from typing import List, Optional
from PySide6.QtCore import Qt, QTimer
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
    QLabel,
    QLineEdit,
    QSplitter,
    QFrame,
)

from src.client.frontend.controllers.app_controller_rich import AppController, ViewInterface
from src.client.frontend.gui_qt.compose_dialog_qt import ComposeDialog
from src.client.frontend.gui_qt.message_view_qt import render_html_to_text
from src.models.email_data import EmailData
from src.common.logger import *


# --------------------------------------------------------------------------
# MAIN WINDOW
# --------------------------------------------------------------------------


class MainWindowQt(QMainWindow, ViewInterface):
    """Improved PySide6 UI with sidebar, 3-pane layout, splitters, search bar, and message header."""

    def __init__(self, username: str, password: str):
        super().__init__()
        self.setWindowTitle("Email Client")
        self.resize(1280, 800)

        self.emails: List[EmailData] = []
        self.selected_email_index: Optional[int] = None

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        # ------------------------------------------------------------------
        # LEFT SIDEBAR (Compose / Refresh / Logout)
        # ------------------------------------------------------------------
        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        # ------------------------------------------------------------------
        # MAIN SPLITTER (Email List <-> Message Pane)
        # ------------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, stretch=1)

        # ----- LEFT PANEL: Email List + Search Bar -----
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search emails...")
        self.search_bar.textChanged.connect(self._filter_emails)
        list_layout.addWidget(self.search_bar)

        # Email List
        self.email_list = QListWidget()
        self.email_list.itemSelectionChanged.connect(self._on_select)
        self.email_list.setStyleSheet(
            """
            QListWidget {
                background: #1e1e1e;
                border: none;
            }
            QListWidget::item {
                background: #2a2a2a;
                padding: 10px;
                margin: 6px 8px;
                border-radius: 8px;
                color: #f0f0f0;
            }
            QListWidget::item:selected {
                background: #3a6ee8;
                color: white;
            }
        """
        )

        list_layout.addWidget(self.email_list, stretch=1)

        splitter.addWidget(list_panel)

        # ----- RIGHT PANEL: Email Header + Body -----
        self.message_panel = self._build_message_viewer()
        splitter.addWidget(self.message_panel)

        splitter.setSizes([400, 800])  # reasonable default proportions

        # ------------------------------------------------------------------
        # STATUS BAR
        # ------------------------------------------------------------------
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.show_status_message("Ready")

        # ------------------------------------------------------------------
        # CONTROLLER (load emails AFTER widgets exist)
        # ------------------------------------------------------------------
        self.controller = AppController(self, username, password)
        self.controller.load_user_emails(self.controller.user)

        # ------------------------------------------------------------------
        # KEYBOARD SHORTCUTS
        # ------------------------------------------------------------------
        self._bind_shortcuts()

    # ----------------------------------------------------------------------
    # SIDEBAR (Vertical toolbar)
    # ----------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(14)

        self.compose_btn = QPushButton("✉️  Compose")
        self.compose_btn.clicked.connect(self.open_compose_window)
        layout.addWidget(self.compose_btn)

        self.refresh_btn = QPushButton("🔄  Refresh")
        self.refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(self.refresh_btn)

        self.reply_btn = QPushButton("↩︎  Reply")
        self.reply_btn.clicked.connect(self._on_reply)
        layout.addWidget(self.reply_btn)

        self.delete_btn = QPushButton("🗑  Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_btn)

        layout.addSpacing(20)

        self.logout_btn = QPushButton("🚪  Logout")
        self.logout_btn.clicked.connect(self.logout)
        layout.addWidget(self.logout_btn)

        return panel

    # ----------------------------------------------------------------------
    # MESSAGE VIEWER PANEL (Header + Body)
    # ----------------------------------------------------------------------

    def _build_message_viewer(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header frame
        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header)

        self.h_from = QLabel("From: ")
        self.h_to = QLabel("To: ")
        self.h_subject = QLabel("Subject: ")
        self.h_date = QLabel("Date: ")

        for widget in (self.h_from, self.h_to, self.h_subject, self.h_date):
            widget.setStyleSheet("font-weight: bold;")

        header_layout.addWidget(self.h_from)
        header_layout.addWidget(self.h_to)
        header_layout.addWidget(self.h_subject)
        header_layout.addWidget(self.h_date)

        layout.addWidget(header)

        # Email body
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        layout.addWidget(self.body, stretch=1)

        return panel

    # ----------------------------------------------------------------------
    # SHORTCUTS
    # ----------------------------------------------------------------------

    def _bind_shortcuts(self):
        self.compose_btn.setShortcut("Ctrl+N")
        self.reply_btn.setShortcut("Ctrl+R")
        self.delete_btn.setShortcut("Delete")
        self.refresh_btn.setShortcut("Ctrl+Shift+R")
        self.logout_btn.setShortcut("Ctrl+Q")

    # ----------------------------------------------------------------------
    # VIEW INTERFACE (CONTROLLER CALLS THESE)
    # ----------------------------------------------------------------------

    def display_emails(self, emails: List[EmailData]):
        self.emails = emails
        self._populate_email_list(emails)

    def _populate_email_list(self, emails: List[EmailData]):
        self.email_list.clear()

        for email in emails:
            item = QListWidgetItem(f"{email.sender}\n{email.subject}")
            item.setData(Qt.ItemDataRole.UserRole, email)
            self.email_list.addItem(item)

        if self.selected_email_index is None or self.selected_email_index >= len(emails):
            self.selected_email_index = None
            self.clear_email_content()

    def display_email_content(self, html_content: str):
        self.body.setPlainText(render_html_to_text(html_content))

    def show_status_message(self, message: str):
        self.status_bar.showMessage(message)

    def clear_email_content(self):
        self.body.clear()
        self.h_from.setText("From:")
        self.h_to.setText("To:")
        self.h_subject.setText("Subject:")
        self.h_date.setText("Date:")

    # ----------------------------------------------------------------------
    # SEARCH FILTER
    # ----------------------------------------------------------------------

    def _filter_emails(self, text: str):
        text = text.lower().strip()
        if not text:
            self._populate_email_list(self.emails)
            return

        filtered = [e for e in self.emails if text in e.subject.lower() or text in e.sender.lower()]
        self._populate_email_list(filtered)

    # ----------------------------------------------------------------------
    # BUTTON CALLBACKS
    # ----------------------------------------------------------------------

    def _on_refresh(self):
        self.controller.refresh_emails()

    def _on_select(self):
        rows = self.email_list.selectedIndexes()
        if not rows:
            return

        idx = rows[0].row()
        self.selected_email_index = idx
        email = self.email_list.item(idx).data(Qt.ItemDataRole.UserRole)

        self.h_from.setText(f"From: {email.sender}")
        self.h_to.setText(f"To: {email.recipient}")
        self.h_subject.setText(f"Subject: {email.subject}")
        self.h_date.setText(f"Date: {email.date}")

        html = email.body_html or f"<pre>{email.body_text}</pre>"
        self.display_email_content(html)

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

    # ----------------------------------------------------------------------
    # COMPOSE
    # ----------------------------------------------------------------------

    def open_compose_window(self, initial_data: Optional[dict] = None):
        dialog = ComposeDialog(self, initial_data or {})
        data = dialog.get_data()
        if data:
            self.controller.send_email(data)

    # ----------------------------------------------------------------------
    # REFRESH BUTTON ENABLE/DISABLE
    # ----------------------------------------------------------------------

    def enable_refresh_button(self, enabled: bool):
        self.refresh_btn.setEnabled(enabled)

    # ----------------------------------------------------------------------
    # LOGOUT
    # ----------------------------------------------------------------------

    def logout(self):
        self.controller.logout()
        self.close()

    # ----------------------------------------------------------------------
    # UI THREAD RUNNER
    # ----------------------------------------------------------------------

    def run_on_ui_thread(self, func, *args, **kwargs):
        QTimer.singleShot(0, lambda: func(*args, **kwargs))
