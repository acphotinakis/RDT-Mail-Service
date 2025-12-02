from dataclasses import dataclass, field
from email.message import Message
from typing import Optional


@dataclass
class EmailData:
    """
    Represents a structured email instance extracted from a MIME Message.

    This class wraps the parsed fields for easy consumption by POP3, SMTP,
    storage layers, UI layers, etc. It preserves the raw MIME for fidelity
    but exposes clean metadata fields.
    """

    raw_message: Message = field(repr=False)
    uid: str
    subject: str
    sender: str
    recipient: str
    date: str

    body_html: Optional[str] = None
    body_text: Optional[str] = None

    # ----------------------------------------------------------------------
    # Properties / Computed Fields
    # ----------------------------------------------------------------------
    @property
    def has_html(self) -> bool:
        return self.body_html is not None

    @property
    def has_text(self) -> bool:
        return self.body_text is not None

    @property
    def mime_size(self) -> int:
        """Returns the approximate size of the MIME message."""
        try:
            return len(self.raw_message.as_string())
        except Exception:
            return 0

    # ----------------------------------------------------------------------
    # Factory constructor for convenience
    # ----------------------------------------------------------------------
    @classmethod
    def from_message(cls, raw: Message, uid: str) -> "EmailData":
        """
        Alternate constructor that extracts required fields from a MIME Message.
        Useful for SMTP incoming processing.
        """
        subject = raw.get("Subject", "(no subject)")
        sender = raw.get("From", "")
        recipient = raw.get("To", "")
        date = raw.get("Date", "")

        # Extract bodies
        body_text, body_html = cls._extract_bodies(raw)

        return cls(
            raw_message=raw,
            uid=uid,
            subject=subject,
            sender=sender,
            recipient=recipient,
            date=date,
            body_html=body_html,
            body_text=body_text,
        )

    # ----------------------------------------------------------------------
    # Internal Body Parsing
    # ----------------------------------------------------------------------
    @staticmethod
    def _extract_bodies(raw: Message) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts text/plain and text/html bodies from a MIME email.
        Pylance-safe and RFC-compliant.
        """
        text_body: Optional[str] = None
        html_body: Optional[str] = None

        def safe_decode(payload, charset: Optional[str]) -> Optional[str]:
            """Decode MIME payload safely regardless of type."""
            if payload is None:
                return None

            if isinstance(payload, bytes):
                try:
                    return payload.decode(charset or "utf-8", errors="replace")
                except Exception:
                    return payload.decode("utf-8", errors="replace")

            if isinstance(payload, str):
                # Already decoded by email module
                return payload

            # Unknown type (edge case)
            return None

        if raw.is_multipart():
            for part in raw.walk():
                content_type = part.get_content_type()
                charset = part.get_content_charset()

                # Multipart containers do not have a payload we care about
                if part.get_content_maintype() == "multipart":
                    continue

                payload = part.get_payload(decode=True)

                if content_type == "text/plain" and text_body is None:
                    text_body = safe_decode(payload, charset)

                elif content_type == "text/html" and html_body is None:
                    html_body = safe_decode(payload, charset)

        else:
            # Single part email
            charset = raw.get_content_charset()
            payload = raw.get_payload(decode=True)
            text_body = safe_decode(payload, charset)

        return text_body, html_body

    # ----------------------------------------------------------------------
    # Introspection / Debugging Helpers
    # ----------------------------------------------------------------------
    def summary(self) -> str:
        """Short one-line description for logs/debugging."""
        return f"Email(uid={self.uid}, from={self.sender}, to={self.recipient}, subject={self.subject})"

    def to_string(self) -> str:
        """Readable, structured diagnostic output."""
        props = {
            "UID": self.uid,
            "Subject": self.subject,
            "Sender": self.sender,
            "Recipient": self.recipient,
            "Date": self.date,
            "Has HTML Body": self.has_html,
            "Has Text Body": self.has_text,
            "Raw MIME Size": self.mime_size,
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nEmailData State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
