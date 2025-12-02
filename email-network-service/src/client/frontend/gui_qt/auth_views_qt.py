from typing import Optional, Tuple, Dict
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QLabel,
    QVBoxLayout,
)
from src.common.logger import *


class LoginDialog(QDialog):
    """Simple login dialog using PySide6."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.result_data: Optional[Tuple[str, str]] = None
        self.setWindowTitle("Login")
        self.resize(360, 200)

        layout = QVBoxLayout(self)
        title = QLabel("Login")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.error_label = QLabel(error_message or "")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        form = QFormLayout()
        layout.addLayout(form)

        self.username_edit = QLineEdit()
        form.addRow("Username", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password", self.password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        log_info_detailed("LoginDialog initialized.")

    def _on_accept(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            log_warning_detailed("Login attempt with empty fields.")
            self.error_label.setText("Both fields are required.")
            return

        log_info_detailed(f"Login attempt for user: {username}")
        self.result_data = (username, password)
        self.accept()

    def get_data(self) -> Optional[Tuple[str, str]]:
        log_debug_detailed("Showing login dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            log_info_detailed("Login dialog accepted.")
            return self.result_data
        log_info_detailed("Login dialog cancelled.")
        return None


class SignupDialog(QDialog):
    """Signup dialog with password confirmation."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.result_data: Optional[Dict[str, str]] = None
        self.setWindowTitle("Sign Up")
        self.resize(360, 240)

        layout = QVBoxLayout(self)
        title = QLabel("Create Account")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.error_label = QLabel(error_message or "")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        form = QFormLayout()
        layout.addLayout(form)

        self.username_edit = QLineEdit()
        form.addRow("Username", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password", self.password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm", self.confirm_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        log_info_detailed("SignupDialog initialized.")

    def _on_accept(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        confirm = self.confirm_edit.text().strip()

        if not username or not password or not confirm:
            log_warning_detailed("Signup attempt with empty fields.")
            self.error_label.setText("All fields are required.")
            return

        if password != confirm:
            log_warning_detailed("Signup attempt with non-matching passwords.")
            self.error_label.setText("Passwords do not match.")
            return

        log_info_detailed(f"Signup attempt for new user: {username}")
        self.result_data = {"user": username, "password": password}
        self.accept()

    def get_data(self) -> Optional[Dict[str, str]]:
        log_debug_detailed("Showing signup dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            log_info_detailed("Signup dialog accepted.")
            return self.result_data
        log_info_detailed("Signup dialog cancelled.")
        return None
