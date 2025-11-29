from typing import Optional, Tuple, Dict
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QLabel,
    QVBoxLayout,
)
from src.common.logger import get_class_logger


class LoginDialog(QDialog):
    """Simple login dialog using PySide6."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.log = get_class_logger(self)
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
        self.log.info("LoginDialog initialized.")

    def _on_accept(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            self.log.warning("Login attempt with empty fields.")
            self.error_label.setText("Both fields are required.")
            return

        self.log.info(f"Login attempt for user: {username}")
        self.result_data = (username, password)
        self.accept()

    def get_data(self) -> Optional[Tuple[str, str]]:
        self.log.debug("Showing login dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            self.log.info("Login dialog accepted.")
            return self.result_data
        self.log.info("Login dialog cancelled.")
        return None


class SignupDialog(QDialog):
    """Signup dialog with password confirmation."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.log = get_class_logger(self)
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
        self.log.info("SignupDialog initialized.")

    def _on_accept(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        confirm = self.confirm_edit.text().strip()

        if not username or not password or not confirm:
            self.log.warning("Signup attempt with empty fields.")
            self.error_label.setText("All fields are required.")
            return

        if password != confirm:
            self.log.warning("Signup attempt with non-matching passwords.")
            self.error_label.setText("Passwords do not match.")
            return

        self.log.info(f"Signup attempt for new user: {username}")
        self.result_data = {"user": username, "password": password}
        self.accept()

    def get_data(self) -> Optional[Dict[str, str]]:
        self.log.debug("Showing signup dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            self.log.info("Signup dialog accepted.")
            return self.result_data
        self.log.info("Signup dialog cancelled.")
        return None
