from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QMessageBox,
)
from src.common.logger import *


class ComposeDialog(QDialog):
    """Modal compose dialog for creating or replying to emails."""

    def __init__(self, parent=None, initial_data: Optional[Dict[str, str]] = None):
        super().__init__(parent)

        self.initial = initial_data or {}
        self.result_data: Optional[Dict[str, str]] = None
        self.setWindowTitle("Compose Email")
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.to_edit = QLineEdit(self.initial.get("recipient", ""))
        form.addRow("To", self.to_edit)

        self.subject_edit = QLineEdit(self.initial.get("subject", ""))
        form.addRow("Subject", self.subject_edit)

        self.body_edit = QTextEdit()
        if "body" in self.initial:
            self.body_edit.setPlainText(self.initial["body"])
        form.addRow("Body", self.body_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        log_info_detailed("ComposeDialog initialized.")
        if self.initial:
            log_debug_detailed(f"Initial data provided: {self.initial}")

    def _on_accept(self):
        recipient = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body = self.body_edit.toPlainText()

        if not recipient or not subject:
            log_warning_detailed("Compose submission failed: recipient or subject is empty.")
            QMessageBox.warning(self, "Validation Error", "To and Subject fields cannot be empty.")
            return

        self.result_data = {"recipient": recipient, "subject": subject, "body": body}
        log_info_detailed(f"Email composed for recipient: {recipient}")
        self.accept()

    def get_data(self) -> Optional[Dict[str, str]]:
        log_debug_detailed("Showing compose dialog.")
        if self.exec() == QDialog.DialogCode.Accepted:
            log_info_detailed("Compose dialog accepted.")
            return self.result_data
        log_info_detailed("Compose dialog cancelled.")
        return None
