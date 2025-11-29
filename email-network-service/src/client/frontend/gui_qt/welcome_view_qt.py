from typing import Optional
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from src.common.logger import get_class_logger


class WelcomeDialog(QDialog):
    """Welcome screen to choose login or signup."""

    def __init__(self, error_message: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.log = get_class_logger(self)
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
        self.log.info("WelcomeDialog initialized.")

    def _choose(self, choice: str):
        self.log.info(f"User chose '{choice}' from welcome screen.")
        self.result_choice = choice
        self.accept()

    def get_choice(self) -> Optional[str]:
        self.log.debug("Showing welcome dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            self.log.info(f"Welcome dialog accepted with choice: {self.result_choice}")
            return self.result_choice
        self.log.info("Welcome dialog cancelled.")
        return None
