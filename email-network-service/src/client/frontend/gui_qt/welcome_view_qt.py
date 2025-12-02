from typing import Optional
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from src.common.logger import *


class WelcomeDialog(QDialog):
    """Welcome screen to choose login or signup."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.result_choice: Optional[str] = None
        self.setWindowTitle("Welcome")
        self.resize(360, 180)

        layout = QVBoxLayout(self)
        title = QLabel("Welcome to the Email Client")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        if error_message:
            err = QLabel(error_message)
            err.setStyleSheet("color: red;")
            layout.addWidget(err)

        buttons = QDialogButtonBox()
        login_btn = buttons.addButton("Login", QDialogButtonBox.ButtonRole.ActionRole)
        signup_btn = buttons.addButton("Sign Up", QDialogButtonBox.ButtonRole.ActionRole)
        cancel_btn = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)

        login_btn.clicked.connect(lambda: self._choose("login"))
        signup_btn.clicked.connect(lambda: self._choose("signup"))
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        log_info_detailed("WelcomeDialog initialized.")

    def _choose(self, choice: str):
        log_info_detailed(f"User chose '{choice}' from welcome screen.")
        self.result_choice = choice
        self.accept()

    def get_choice(self) -> Optional[str]:
        log_debug_detailed("Showing welcome dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            log_info_detailed(f"Welcome dialog accepted with choice: {self.result_choice}")
            return self.result_choice
        log_info_detailed("Welcome dialog cancelled.")
        return None
