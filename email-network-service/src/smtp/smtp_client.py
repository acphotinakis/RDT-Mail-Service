"""
Implements an SMTP client for sending emails.

This module provides `SMTPClient`, a class that handles the client-side
of the SMTP protocol. It uses the Reliable Data Transfer (RDT) protocol
over UDP to communicate with an SMTP server. The client is responsible for
the entire email sending transaction, from the initial handshake to sending
the email data and closing the connection.
"""

import socket
from typing import Optional, Tuple
from src.common.logger import get_class_logger
from src.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    CLIENT_IP,
    RDT_TIMEOUT,
)
from src.rdt.rdt_config import MAX_PAYLOAD_SIZE
from src.common.exceptions import SMTPProtocolError, SMTPConnectionError
from src.rdt.rdt_sender import RDTSender
from src.rdt.rdt_receiver import RDTReceiver
from src.rdt.rdt_dispatcher import RDTDispatcher

# SMTP Response Codes
SMTP_READY = 220
SMTP_OK = 250
SMTP_CLOSING = 221
SMTP_START_INPUT = 354


class SMTPClient:
    """
    An SMTP client that sends emails using the RDT protocol over UDP.

    This class encapsulates the entire SMTP workflow for sending an email. It
    manages a UDP socket, an RDT sender and receiver, and the sequence of SMTP
    commands required to complete an email transaction.

    The client binds to an ephemeral port, allowing multiple instances to run
    concurrently.

    Attributes:
        log: A logger instance for the class.
        sock (socket.socket): The UDP socket used for communication.
        dispatcher (RDTDispatcher): The dispatcher managing incoming RDT packets.
        rdt_sender (RDTSender): The RDT sender for reliable data transmission.
        rdt_receiver (RDTReceiver): The RDT receiver for reliable data reception.
        receiver_gen: A generator for receiving RDT packets.
        is_connected (bool): A flag indicating the connection state.
    """

    def __init__(self):
        """
        Initializes the SMTPClient.

        This sets up the UDP socket, binds it to an ephemeral port, and
        initializes the RDT dispatcher, sender, and receiver components.

        Side Effects:
            - Creates and binds a UDP socket.
            - Starts a background thread for the RDT dispatcher.
        """
        self.log = get_class_logger(self)

        # 1. Socket Setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Use Port 0 (Ephemeral) so the OS assigns a random available port.
        # This allows multiple SMTPClient instances to run in parallel threads.
        self.sock.bind((CLIENT_IP, 0))
        self.sock.settimeout(RDT_TIMEOUT)

        # 2. RDT Setup
        self.dispatcher = RDTDispatcher(self.sock)
        self.dispatcher.start()

        self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)
        self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
        self.receiver_gen = self.rdt_receiver.start_receiving()

        self.is_connected = False

    def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
        """
        Sends an email by executing the full SMTP transaction.

        Args:
            sender (str): The sender's email address.
            recipient (str): The recipient's email address.
            subject (str): The subject of the email.
            body (str): The body content of the email.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        try:
            self._connect()
            self._do_handshake()
            self._send_mail_from(sender)
            self._send_rcpt_to(recipient)
            self._send_data(subject, body)
            self._send_quit()
            return True
        except Exception as e:
            self.log.error(f"Email transaction failed: {e}")
            if self.is_connected:
                try:
                    self._send_command("QUIT")
                except:
                    pass
            return False
        finally:
            self._close()

    def _connect(self):
        """
        Establishes a connection to the SMTP server.

        Instead of sending an empty RDT packet (which is an implementation detail hack),
        this method sends a standard 'NOOP' command. This serves two purposes:
        1. It acts as a concrete Application Layer handshake, forcing the server to
           initialize the session and send the '220' Welcome banner.
        2. It ensures the first packet contains valid SMTP protocol data.

        Raises:
            SMTPConnectionError: If the server does not respond with the expected code.
        """
        self.receiver_gen = self.rdt_receiver.start_receiving()

        # Send NOOP to initiate the session
        self._send_command("NOOP")

        # 1. Expect Welcome Message (220) from Session Creation
        try:
            code, msg = self._get_reply()
            if code != SMTP_READY:
                raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
        except Exception as e:
            raise SMTPConnectionError(f"Connection failed during handshake: {e}")

        # 2. Expect Response to NOOP (250)
        # We must consume this response so it doesn't interfere with the subsequent HELO.
        try:
            code_noop, _ = self._get_reply()
            if code_noop != SMTP_OK:
                self.log.warning(f"Initial NOOP handshake returned code: {code_noop}")
        except Exception:
            # If the server is modified in the future to not send 250 for the
            # trigger packet, we ignore read errors here to remain robust.
            pass

        self.is_connected = True

    def _do_handshake(self):
        """
        Performs the SMTP `HELO` handshake.

        Raises:
            SMTPProtocolError: If the server does not respond with a `250 OK`.
        """
        self._send_command("HELO localhost")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("HELO failed")

    def _send_mail_from(self, sender: str):
        """
        Sends the `MAIL FROM` command.
        """
        self._send_command(f"MAIL FROM:<{sender}>")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("MAIL FROM failed")

    def _send_rcpt_to(self, recipient: str):
        """
        Sends the `RCPT TO` command.
        """
        self._send_command(f"RCPT TO:<{recipient}>")
        code, _ = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError("RCPT TO failed")

    def _send_data(self, subject: str, body: str):
        """
        Sends the `DATA` command and the email content.
        """
        self._send_command("DATA")
        code, msg = self._get_reply()
        if code != SMTP_START_INPUT:
            raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

        # --- CHUNKING LOGIC ---
        full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
        payload_bytes = full_payload.encode("ascii")
        total_len = len(payload_bytes)
        sent = 0

        while sent < total_len:
            chunk = payload_bytes[sent : sent + MAX_PAYLOAD_SIZE]
            self.rdt_sender.send(chunk)
            sent += len(chunk)

        code, msg = self._get_reply()
        if code != SMTP_OK:
            raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

    def _send_quit(self):
        """
        Sends the `QUIT` command to terminate the SMTP session.
        """
        self._send_command("QUIT")
        try:
            self._get_reply()
        except:
            pass
        self.is_connected = False

    def _send_command(self, cmd: str):
        """
        Sends an SMTP command string to the server via the RDT sender.
        Appends CRLF as required by protocol.
        """
        self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

    def _get_reply(self) -> Tuple[int, str]:
        """
        Receives and parses a reply from the SMTP server.

        Returns:
            Tuple[int, str]: Status code and message.
        """
        try:
            data_bytes, _ = next(self.receiver_gen)
            reply = data_bytes.decode("ascii").strip()

            if len(reply) < 3:
                raise SMTPProtocolError(f"Malformed reply: {reply}")

            code = int(reply[:3])
            msg = reply[4:] if len(reply) > 4 else ""
            return code, msg
        except StopIteration:
            raise SMTPConnectionError("Connection closed")

    def _close(self):
        """
        Closes the socket and stops the RDT dispatcher thread.
        """
        if self.dispatcher:
            self.dispatcher.stop()
        if self.sock:
            self.sock.close()


# """
# Implements an SMTP client for sending emails.

# This module provides `SMTPClient`, a class that handles the client-side
# of the SMTP protocol. It uses the Reliable Data Transfer (RDT) protocol
# over UDP to communicate with an SMTP server. The client is responsible for
# the entire email sending transaction, from the initial handshake to sending
# the email data and closing the connection.
# """

# import socket
# from typing import Optional, Tuple
# from src.common.logger import get_class_logger
# from config import (
#     SMTP_SERVER_HOST,
#     SMTP_SERVER_PORT,
#     CLIENT_IP,
#     RDT_TIMEOUT,
# )
# from rdt.rdt_config import MAX_PAYLOAD_SIZE
# from src.common.exceptions import SMTPProtocolError, SMTPConnectionError
# from rdt.rdt_sender import RDTSender
# from rdt.rdt_receiver import RDTReceiver
# from rdt.rdt_dispatcher import RDTDispatcher

# # SMTP Response Codes
# SMTP_READY = 220
# SMTP_OK = 250
# SMTP_CLOSING = 221
# SMTP_START_INPUT = 354


# class SMTPClient:
#     """
#     An SMTP client that sends emails using the RDT protocol over UDP.

#     This class encapsulates the entire SMTP workflow for sending an email. It
#     manages a UDP socket, an RDT sender and receiver, and the sequence of SMTP
#     commands required to complete an email transaction.

#     The client binds to an ephemeral port, allowing multiple instances to run
#     concurrently.

#     Attributes:
#         log: A logger instance for the class.
#         sock (socket.socket): The UDP socket used for communication.
#         dispatcher (RDTDispatcher): The dispatcher managing incoming RDT packets.
#         rdt_sender (RDTSender): The RDT sender for reliable data transmission.
#         rdt_receiver (RDTReceiver): The RDT receiver for reliable data reception.
#         receiver_gen: A generator for receiving RDT packets.
#         is_connected (bool): A flag indicating the connection state.
#     """

#     def __init__(self):
#         """
#         Initializes the SMTPClient.

#         This sets up the UDP socket, binds it to an ephemeral port, and
#         initializes the RDT dispatcher, sender, and receiver components.

#         Side Effects:
#             - Creates and binds a UDP socket.
#             - Starts a background thread for the RDT dispatcher.

#         """
#         self.log = get_class_logger(self)

#         # 1. Socket Setup
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

#         # --- CRITICAL FIX ---
#         # Use Port 0 (Ephemeral) so the OS assigns a random available port.
#         # This allows multiple SMTPClient instances to run in parallel threads.
#         self.sock.bind((CLIENT_IP, 0))

#         self.sock.settimeout(RDT_TIMEOUT)

#         # 2. RDT Setup
#         self.dispatcher = RDTDispatcher(self.sock)
#         self.dispatcher.start()

#         self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)
#         self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
#         self.receiver_gen = self.rdt_receiver.start_receiving()

#         self.is_connected = False
#         # self.log.info("SMTPClient initialized.")

#     def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
#         """
#         Sends an email by executing the full SMTP transaction.

#         This is the main public method of the class. It orchestrates the
#         entire process of connecting, handshaking, and sending the email
#         data. It ensures that resources are cleaned up properly, even if an
#         error occurs.

#         Args:
#             sender (str): The sender's email address.
#             recipient (str): The recipient's email address.
#             subject (str): The subject of the email.
#             body (str): The body content of the email.

#         Returns:
#             bool: True if the email was sent successfully, False otherwise.

#         """
#         try:
#             self._connect()
#             self._do_handshake()
#             self._send_mail_from(sender)
#             self._send_rcpt_to(recipient)
#             self._send_data(subject, body)
#             self._send_quit()
#             # self.log.info("Email transaction completed successfully.")
#             return True
#         except Exception as e:
#             self.log.error(f"Email transaction failed: {e}")
#             if self.is_connected:
#                 try:
#                     self._send_command("QUIT")
#                 except:
#                     pass
#             return False
#         finally:
#             self._close()

#     def _connect(self):
#         """
#         Establishes a connection to the SMTP server.

#         It sends an initial empty packet to elicit the server's `220 Ready`
#         welcome message.

#         Raises:
#             SMTPConnectionError: If the server does not respond with the
#                 expected `220` code.

#         """
#         self.receiver_gen = self.rdt_receiver.start_receiving()
#         # Send empty packet to trigger server welcome
#         self.rdt_sender.send(b"")
#         code, msg = self._get_reply()
#         if code != SMTP_READY:
#             raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
#         self.is_connected = True

#     def _do_handshake(self):
#         """
#         Performs the SMTP `HELO` handshake.

#         Raises:
#             SMTPProtocolError: If the server does not respond with a `250 OK`
#                 code.

#         """
#         self._send_command("HELO localhost")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("HELO failed")

#     def _send_mail_from(self, sender: str):
#         """
#         Sends the `MAIL FROM` command.

#         Args:
#             sender (str): The sender's email address.

#         Raises:
#             SMTPProtocolError: If the server does not respond with `250 OK`.

#         """
#         self._send_command(f"MAIL FROM:<{sender}>")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("MAIL FROM failed")

#     def _send_rcpt_to(self, recipient: str):
#         """
#         Sends the `RCPT TO` command.

#         Args:
#             recipient (str): The recipient's email address.

#         Raises:
#             SMTPProtocolError: If the server does not respond with `250 OK`.

#         """
#         self._send_command(f"RCPT TO:<{recipient}>")
#         code, _ = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError("RCPT TO failed")

#     def _send_data(self, subject: str, body: str):
#         """
#         Sends the `DATA` command and the email content.

#         After sending the `DATA` command, it waits for the server's `354 Start
#         mail input` response. It then sends the email content, formatted with
#         headers and the terminating `.` character, in chunks if necessary.

#         Args:
#             subject (str): The email subject.
#             body (str): The email body.

#         Raises:
#             SMTPProtocolError: If the server does not respond correctly to the
#                 `DATA` command or after the data has been sent.

#         """
#         self._send_command("DATA")
#         code, msg = self._get_reply()
#         if code != SMTP_START_INPUT:
#             raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

#         # --- CHUNKING LOGIC ---
#         full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
#         payload_bytes = full_payload.encode("ascii")
#         total_len = len(payload_bytes)
#         sent = 0

#         # self.log.debug(f"Sending {total_len} bytes in chunks of {MAX_PAYLOAD_SIZE}...")

#         while sent < total_len:
#             chunk = payload_bytes[sent : sent + MAX_PAYLOAD_SIZE]
#             self.rdt_sender.send(chunk)
#             sent += len(chunk)

#         code, msg = self._get_reply()
#         if code != SMTP_OK:
#             raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

#     def _send_quit(self):
#         """
#         Sends the `QUIT` command to terminate the SMTP session.

#         """
#         self._send_command("QUIT")
#         try:
#             self._get_reply()
#         except:
#             pass
#         self.is_connected = False

#     def _send_command(self, cmd: str):
#         """
#         Sends an SMTP command string to the server via the RDT sender.

#         The command is appended with `\\r\\n` as required by the SMTP protocol.

#         Args:
#             cmd (str): The SMTP command to send.

#         """
#         self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

#     def _get_reply(self) -> Tuple[int, str]:
#         """
#         Receives and parses a reply from the SMTP server.

#         It waits for the next packet from the RDT receiver, decodes it, and
#         parses the 3-digit status code and the reply message.

#         Returns:
#             Tuple[int, str]: A tuple containing the integer status code and the
#                 reply message string.

#         Raises:
#             SMTPProtocolError: If the server's reply is malformed.
#             SMTPConnectionError: If the connection is closed while waiting for a reply.

#         """
#         # Always expects (data, addr) tuple now
#         try:
#             data_bytes, _ = next(self.receiver_gen)
#             reply = data_bytes.decode("ascii").strip()

#             if len(reply) < 3:
#                 raise SMTPProtocolError(f"Malformed reply: {reply}")

#             code = int(reply[:3])
#             msg = reply[4:] if len(reply) > 4 else ""
#             return code, msg
#         except StopIteration:
#             raise SMTPConnectionError("Connection closed")

#     def _close(self):
#         """
#         Closes the socket and stops the RDT dispatcher thread.

#         This method should be called to ensure a clean shutdown of the client.

#         """
#         if self.dispatcher:
#             self.dispatcher.stop()
#         if self.sock:
#             self.sock.close()


# # import socket
# # from typing import Optional, Tuple
# # from src.common.logger import get_class_logger
# # from config import (
# #     SMTP_SERVER_HOST,
# #     SMTP_SERVER_PORT,
# #     CLIENT_IP,
# #     CLIENT_LISTENING_PORT,
# #     RDT_TIMEOUT,
# # )
# # from rdt.rdt_config import MAX_PAYLOAD_SIZE
# # from src.common.exceptions import SMTPProtocolError, SMTPConnectionError
# # from rdt.rdt_sender import RDTSender
# # from rdt.rdt_receiver import RDTReceiver
# # from rdt.rdt_dispatcher import RDTDispatcher

# # # SMTP Response Codes
# # SMTP_READY = 220
# # SMTP_OK = 250
# # SMTP_CLOSING = 221
# # SMTP_START_INPUT = 354


# # class SMTPClient:
# #     def __init__(self):
# #         self.log = get_class_logger(self)

# #         # 1. Socket Setup
# #         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #         self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# #         self.sock.bind((CLIENT_IP, CLIENT_LISTENING_PORT))
# #         self.sock.settimeout(RDT_TIMEOUT)

# #         # 2. RDT Setup
# #         self.dispatcher = RDTDispatcher(self.sock)
# #         self.dispatcher.start()

# #         self.rdt_sender = RDTSender(SMTP_SERVER_HOST, SMTP_SERVER_PORT, self.dispatcher)

# #         # REMOVED confusing yield_addr=False flag.
# #         self.rdt_receiver = RDTReceiver(dispatcher=self.dispatcher)
# #         self.receiver_gen = self.rdt_receiver.start_receiving()

# #         self.is_connected = False
# #         self.log.info("SMTPClient initialized.")

# #     def send_email(self, sender: str, recipient: str, subject: str, body: str) -> bool:
# #         try:
# #             self._connect()
# #             self._do_handshake()
# #             self._send_mail_from(sender)
# #             self._send_rcpt_to(recipient)
# #             self._send_data(subject, body)
# #             self._send_quit()
# #             self.log.info("Email transaction completed successfully.")
# #             return True
# #         except Exception as e:
# #             self.log.error(f"Email transaction failed: {e}")
# #             if self.is_connected:
# #                 try:
# #                     self._send_command("QUIT")
# #                 except:
# #                     pass
# #             return False
# #         finally:
# #             self._close()

# #     def _connect(self):
# #         self.receiver_gen = self.rdt_receiver.start_receiving()
# #         # Send empty packet to trigger server welcome
# #         self.rdt_sender.send(b"")
# #         code, msg = self._get_reply()
# #         if code != SMTP_READY:
# #             raise SMTPConnectionError(f"Server not ready. Got: {code} {msg}")
# #         self.is_connected = True

# #     def _do_handshake(self):
# #         self._send_command("HELO localhost")
# #         code, _ = self._get_reply()
# #         if code != SMTP_OK:
# #             raise SMTPProtocolError("HELO failed")

# #     def _send_mail_from(self, sender: str):
# #         self._send_command(f"MAIL FROM:<{sender}>")
# #         code, _ = self._get_reply()
# #         if code != SMTP_OK:
# #             raise SMTPProtocolError("MAIL FROM failed")

# #     def _send_rcpt_to(self, recipient: str):
# #         self._send_command(f"RCPT TO:<{recipient}>")
# #         code, _ = self._get_reply()
# #         if code != SMTP_OK:
# #             raise SMTPProtocolError("RCPT TO failed")

# #     def _send_data(self, subject: str, body: str):
# #         self._send_command("DATA")
# #         code, msg = self._get_reply()
# #         if code != SMTP_START_INPUT:
# #             raise SMTPProtocolError(f"DATA command rejected: {code} {msg}")

# #         # --- CHUNKING LOGIC ---
# #         full_payload = f"Subject: {subject}\r\n\r\n{body}\r\n.\r\n"
# #         payload_bytes = full_payload.encode("ascii")
# #         total_len = len(payload_bytes)
# #         sent = 0

# #         self.log.debug(f"Sending {total_len} bytes in chunks of {MAX_PAYLOAD_SIZE}...")

# #         while sent < total_len:
# #             chunk = payload_bytes[sent : sent + MAX_PAYLOAD_SIZE]
# #             self.rdt_sender.send(chunk)
# #             sent += len(chunk)

# #         code, msg = self._get_reply()
# #         if code != SMTP_OK:
# #             raise SMTPProtocolError(f"Data finalization failed: {code} {msg}")

# #     def _send_quit(self):
# #         self._send_command("QUIT")
# #         try:
# #             self._get_reply()
# #         except:
# #             pass
# #         self.is_connected = False

# #     def _send_command(self, cmd: str):
# #         self.rdt_sender.send((cmd + "\r\n").encode("ascii"))

# #     def _get_reply(self) -> Tuple[int, str]:
# #         # Always expects (data, addr) tuple now
# #         try:
# #             data_bytes, _ = next(self.receiver_gen)
# #             reply = data_bytes.decode("ascii").strip()

# #             if len(reply) < 3:
# #                 raise SMTPProtocolError(f"Malformed reply: {reply}")

# #             code = int(reply[:3])
# #             msg = reply[4:] if len(reply) > 4 else ""
# #             return code, msg
# #         except StopIteration:
# #             raise SMTPConnectionError("Connection closed")

# #     def _close(self):
# #         if self.dispatcher:
# #             self.dispatcher.stop()
# #         if self.sock:
# #             self.sock.close()
