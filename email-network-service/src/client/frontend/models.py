from dataclasses import dataclass, field
from email.message import Message
from typing import Optional, List
from PySide6.QtCore import QAbstractListModel, Qt

@dataclass
class EmailData:
    uid: str
    subject: str
    sender: str
    recipient: str
    date: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    raw_message: Message = field(repr=False)

class EmailListModel(QAbstractListModel):
    def __init__(self, *args, emails: Optional[List[EmailData]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.emails = emails or []

    def rowCount(self, parent):
        return len(self.emails)

    def data(self, index, role):
        if not index.isValid():
            return None
        
        if role == Qt.DisplayRole:
            email = self.emails[index.row()]
            return f"{email.sender}\n{email.subject}\n{email.date}"
        
        # Add a custom role to get the full EmailData object
        if role == Qt.UserRole:
            return self.emails[index.row()]
            
        return None

    def update_emails(self, emails: List[EmailData]):
        self.beginResetModel()
        self.emails = emails
        self.endResetModel()
