from PySide6.QtWidgets import QWidget, QVBoxLayout, QDialog, QLineEdit, QTextEdit, QPushButton, QFormLayout, QHBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Signal
from typing import Optional

# TODO: Install PySide6-WebEngine: pip install PySide6-WebEngine

class MessageView(QWidget):
    def __init__(self):
        super().__init__()
        self.web_view = QWebEngineView()
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        self.setLayout(layout)
    
    def setHtml(self, html):
        self.web_view.setHtml(html)

class ComposeWindow(QDialog):
    """A dialog window for composing and sending an email."""
    send_request = Signal(dict)

    def __init__(self, parent=None, initial_data: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Compose New Message")
        self.setMinimumWidth(600)

        # Widgets
        self.to_field = QLineEdit()
        self.subject_field = QLineEdit()
        self.body_field = QTextEdit()
        self.send_button = QPushButton("Send")
        self.discard_button = QPushButton("Discard")

        # Layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("To:", self.to_field)
        form_layout.addRow("Subject:", self.subject_field)
        layout.addLayout(form_layout)
        layout.addWidget(self.body_field)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.discard_button)
        button_layout.addWidget(self.send_button)
        layout.addLayout(button_layout)

        # Pre-populate fields if data is provided
        if initial_data:
            self.to_field.setText(initial_data.get("recipient", ""))
            self.subject_field.setText(initial_data.get("subject", ""))
            self.body_field.setPlainText(initial_data.get("body", ""))

        # Signals
        self.send_button.clicked.connect(self.on_send)
        self.discard_button.clicked.connect(self.reject)

    def on_send(self):
        """Emits the send_request signal with the email data and closes."""
        email_data = {
            "recipient": self.to_field.text(),
            "subject": self.subject_field.text(),
            "body": self.body_field.toPlainText(),
        }
                self.send_request.emit(email_data)
                self.accept()
        
        class SettingsDialog(QDialog):
            """A dialog for configuring user and server settings."""
            def __init__(self, parent=None, settings: Optional[dict] = None):
                super().__init__(parent)
                self.setWindowTitle("Settings")
        
                # Widgets
                self.user_field = QLineEdit()
                self.password_field = QLineEdit()
                self.password_field.setEchoMode(QLineEdit.Password)
                self.save_button = QPushButton("Save")
                self.cancel_button = QPushButton("Cancel")
        
                # Layout
                layout = QVBoxLayout(self)
                form_layout = QFormLayout()
                form_layout.addRow("User:", self.user_field)
                form_layout.addRow("Password:", self.password_field)
                layout.addLayout(form_layout)
        
                button_layout = QHBoxLayout()
                button_layout.addStretch()
                button_layout.addWidget(self.cancel_button)
                button_layout.addWidget(self.save_button)
                layout.addLayout(button_layout)
        
                # Pre-populate
                if settings:
                    self.user_field.setText(settings.get("user", ""))
                    self.password_field.setText(settings.get("password", ""))
        
                # Signals
                self.save_button.clicked.connect(self.accept)
                self.cancel_button.clicked.connect(self.reject)
        
            def get_settings(self) -> dict:
                """Returns the settings entered in the dialog."""
                return {
                    "user": self.user_field.text(),
                    "password": self.password_field.text(),
                }
        