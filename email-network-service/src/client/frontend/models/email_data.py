from dataclasses import dataclass, field
from email.message import Message
from typing import Optional


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
