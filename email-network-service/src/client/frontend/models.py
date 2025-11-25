from dataclasses import dataclass, field
from email.message import Message
from typing import Optional, List
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QPersistentModelIndex


@dataclass
class EmailData:
    raw_message: Message = field(repr=False)
    uid: str
    subject: str
    sender: str
    recipient: str
    date: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None


class EmailListModel(QAbstractListModel):
    def __init__(self, *args, emails: Optional[List[EmailData]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.emails = emails or []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self.emails)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            email = self.emails[index.row()]
            return f"{email.sender}\n{email.subject}\n{email.date}"

        # Add a custom role to get the full EmailData object
        if role == Qt.ItemDataRole.UserRole:
            return self.emails[index.row()]

        return None

    def update_emails(self, emails: List[EmailData]):
        self.beginResetModel()
        self.emails = emails
        self.endResetModel()
