"""
File: src/common/exceptions.py
----------------------------------------
Description:
    Custom exception classes for the Email Network Service.
    These allow the application to handle specific protocol failures
    gracefully (e.g., distinguishing between a network timeout and
    a bad password).
"""


class EmailServiceError(Exception):
    """Base exception class for all custom errors in this project."""

    pass


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

    pass


class SMTPConnectionError(EmailServiceError):
    """
    Raised when the connection to the SMTP server fails.
    Examples:
        - Server is down / unreachable.
        - Connection timed out during handshake.
        - RDT transport layer failure.
    """

    pass


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

    pass


class POP3ConnectionError(EmailServiceError):
    """
    Raised when connection to the POP3 server fails.
    """

    pass


# ------------------------------------------------------------------------------
# RDT / Transport Exceptions
# ------------------------------------------------------------------------------


class RDTTimeoutError(EmailServiceError):
    """Raised when the RDT layer times out waiting for an expected packet."""

    pass


class RDTPacketError(EmailServiceError):
    """Raised when a packet is corrupt or cannot be parsed."""

    pass
