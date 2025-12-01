"""
File: src/common/exceptions.py
----------------------------------------
Description:
    Custom exception classes for the Email Network Service.
    These allow the application to handle specific protocol failures
    gracefully (e.g., distinguishing between a network timeout and
    a bad password).
"""

from typing import Dict, Optional


class EmailServiceError(Exception):
    """Base exception class for all custom errors in this project."""

    def __init__(self, message: str = "", *, context: Optional[Dict[str, object]] = None):
        self.message = message or self.__class__.__name__
        # Filter out None entries so __str__ stays compact.
        self.context = {k: v for k, v in (context or {}).items() if v is not None}
        super().__init__(self.message)

    def __str__(self) -> str:
        if not self.context:
            return self.message
        kv_pairs = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.message} ({kv_pairs})"


# ------------------------------------------------------------------------------
# SMTP Exceptions
# ------------------------------------------------------------------------------


class SMTPProtocolError(EmailServiceError):
    """
    Raised when the SMTP conversation violates the protocol rules.
    Examples:
        - Receiving a 500 error from the server.
        - Receiving garbage data instead of a response code.
        - Sending commands out of order.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[int] = None,
        command: Optional[str] = None,
        response: Optional[str] = None,
    ):
        context = {"code": code, "command": command, "response": response}
        super().__init__(message, context=context)
        self.code = code
        self.command = command
        self.response = response


class SMTPConnectionError(EmailServiceError):
    """
    Raised when the connection to the SMTP server fails.
    Examples:
        - Server is down / unreachable.
        - Connection timed out during handshake.
        - RDT transport layer failure.
    """

    def __init__(
        self,
        message: str,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reason: Optional[str] = None,
    ):
        context = {"host": host, "port": port, "reason": reason}
        super().__init__(message, context=context)
        self.host = host
        self.port = port
        self.reason = reason


# ------------------------------------------------------------------------------
# POP3 Exceptions
# ------------------------------------------------------------------------------


class POP3ProtocolError(EmailServiceError):
    """
    Raised when the POP3 conversation violates protocol rules.
    Examples:
        - Authentication failure (-ERR response).
        - Malformed server responses.
    """

    def __init__(
        self,
        message: str,
        *,
        command: Optional[str] = None,
        response: Optional[str] = None,
    ):
        context = {"command": command, "response": response}
        super().__init__(message, context=context)
        self.command = command
        self.response = response


class POP3ConnectionError(EmailServiceError):
    """
    Raised when connection to the POP3 server fails.
    """

    def __init__(
        self,
        message: str,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reason: Optional[str] = None,
    ):
        context = {"host": host, "port": port, "reason": reason}
        super().__init__(message, context=context)
        self.host = host
        self.port = port
        self.reason = reason


# ------------------------------------------------------------------------------
# RDT / Transport Exceptions
# ------------------------------------------------------------------------------


class RDTTimeoutError(EmailServiceError):
    """Raised when the RDT layer times out waiting for an expected packet."""

    def __init__(
        self,
        message: str,
        *,
        seq: Optional[int] = None,
        retries: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        context = {"seq": seq, "retries": retries, "timeout": timeout}
        super().__init__(message, context=context)
        self.seq = seq
        self.retries = retries
        self.timeout = timeout


class RDTPacketError(EmailServiceError):
    """Raised when a packet is corrupt or cannot be parsed."""

    def __init__(
        self,
        message: str,
        *,
        packet_bytes: Optional[bytes] = None,
        detail: Optional[str] = None,
    ):
        context = {
            "packet_preview": packet_bytes[:32] if packet_bytes else None,
            "detail": detail,
        }
        super().__init__(message, context=context)
        self.packet_bytes = packet_bytes
        self.detail = detail
