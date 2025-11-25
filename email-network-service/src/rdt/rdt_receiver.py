"""
File: receiver.py
----------------------------------------
Description:
    Provides Selective Repeat functionality in the UDP protocol for receiving packets.

Author:
    Caleb Talbott

Last Edited:
    2025-11-1
"""

import pickle
import socket
from src.rdt.rdt_util import calculate_checksum
from src.common.logger import get_class_logger


class RDTReceiver:
    """Provides Selective Repeat functionality in the UDP protocol for receiving packets."""

    def __init__(
        self, port: int, src_address="127.0.0.1", dst_address="127.0.0.1", window_size=8
    ):
        """
        Constructor for an RDT packet receiver.

        Args:
            port (int): The base port for the RDT receiver is configured accordingly. The sending port is set to the
                        specified port, while the receiving port is set to one increment above the specified port.
            timeout (int):  The amount of time the sender will wait before retransmitting unACKed packets. Default: 4
            src_address (str):  The address of the receiver's host. Default: 127.0.0.1
            dst_address (str):  The address of the sender's host. Default: 127.0.0.1
            window_size (int):  The size of the window including sequence number that can be sent in the protocol. Default: 8
        """
        self.log = get_class_logger(self)
        self.log.info("RDTReceiver initialized")

        self.src_address = src_address
        self.dst_address = dst_address
        self.port = port
        self.log.info(f"Receiver Ports: {port}")

        # Only need one socket for receiver
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((src_address, port))
        self.socket.listen(1)
        self.conn = None
        self.addr = None

        # Initialize the status flags for the receiver
        self.is_receiving = False

        # A protocol must implement the same window size in sender and receiver
        self.window_size = window_size
        self.recv_base = 0
        self.window = {}
        self.ordered_chunks = []

    def start_accepting(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.src_address, self.port))
            self.socket.listen(1)

        try:
            self.socket.settimeout(1)  # Allows for clean shutdown
            self.conn, self.addr = self.socket.accept()
            self.log.info(f"{self.conn}, {self.addr}")
            return True
        except socket.timeout:
            return False

    def receive_packet(self) -> bytes | None:
        """
        A blocking function that waits for a stream of bytes in the socket.

        Returns:
            (bytes | None): Returns the packet received in bytes or None if there was an error.
        """
        try:
            pkt_len = self.conn.recv(4)
            if not pkt_len:
                return None

            length = int.from_bytes(pkt_len, "big")
            data = b""
            while len(data) < length:
                payload = self.conn.recv(length - len(data))
                if not payload:
                    return None
                data += payload

            return data
        except Exception:
            return None

    def verify_packet(self, data: bytes):
        """
        Checks whether a packet contains the necessary fields and if the packet is corrupted.

        Args:
            data (bytes): The packet to validate in bytes.

        Returns:
            (bool): Whether the packet is valid or not.
        """
        pkt = pickle.loads(data)  # Deserialize the packet
        # Check if the packet contains necessary information for the protocol
        if (
            "final" not in pkt
            or "seq" not in pkt
            or "data" not in pkt
            or "checksum" not in pkt
        ):
            self.log.error("Receiver: Packet missing required fields!")
            return False

        # Compute if the data payload contains a valid UDP checksum
        valid_checksum = pkt["checksum"] == calculate_checksum(
            pickle.dumps(
                {"final": pkt["final"], "seq": pkt["seq"], "data": pkt["data"]}
            )
        )
        self.log.debug(f"Receiver: Valid Checksum {pkt['seq']}: {valid_checksum}")
        return valid_checksum

    def receive_messages(self) -> list[bytes]:
        """
        Accepts packets from a single sender. Will maintain sequence order and stores the ordered packets in the
        "ordered_chunks" list. If a termination packet is received, this function will send a FIN ACK packet to the
        sender and will close the socket.

        Returns:
            Will return early if the socket cannot be bound to the receiving port.
        """
        if not self.conn:
            self.log.error("Connection not established!")
            return []
        self.log.debug(f"{self.conn}, {self.socket}")

        self.log.info("Receiver: Accepting Messages!")
        # Indicate that the receiver is receiving and that a termination has not been initiated.
        self.is_receiving = True
        last_pkt_received = False

        # Loop until the receiver indicates that it is no longer accepting packets.
        while self.is_receiving:
            # Wait until a packet is received.
            data = self.receive_packet()
            # Empty packet, ignore
            if data is None:
                self.log.info(f"Receiver [{self.port}]: Sender has closed connection!")
                self.cleanup()
                self.is_receiving = False
                return self.deliver_chunks()
            # Invalid packet, ignore
            if not self.verify_packet(data):
                continue

            # Deserialize the packet into a dictionary
            pkt = pickle.loads(data)
            seq_num = pkt["seq"]

            # If the packet includes a termination field of True, send a FIN ACK packet and terminate connection.
            if pkt["final"]:
                last_pkt_received = True
                self.log.debug(f"Receiver: Received final packet at SEQ {seq_num}")

            # Check if the received packet is in the receiver's window
            if self.recv_base <= seq_num < self.recv_base + self.window_size:
                self.conn.sendall(pickle.dumps({"ack": seq_num}))
                self.window[seq_num] = pkt

                # Send all ACKs and deliver chunks until a packet in the window has not been received.
                while self.recv_base in self.window:
                    current_pkt = self.window.pop(self.recv_base)
                    self.ordered_chunks.append(current_pkt["data"])
                    self.recv_base += 1

            # If a packet has been received that is not in the window, send the corresponding ACK.
            elif self.recv_base - self.window_size <= seq_num < self.recv_base:
                self.conn.sendall(pickle.dumps({"ack": seq_num}))

            # Exit the receiving loop if the termination sequence has begun and there is no packets left in the window.
            if last_pkt_received and len(self.window) == 0:
                self.is_receiving = False
                break

        return self.deliver_chunks()

    def deliver_chunks(self):
        self.log.debug(f"Receiver: {self.ordered_chunks}")
        chunks = self.ordered_chunks.copy()
        self.ordered_chunks.clear()
        self.log.debug(f"Receiver: {chunks}")
        return chunks

    def terminate_connection(self):
        """
        Sets the receiver's terminated status flags and close the receiving socket.
        """
        if self.conn:
            self.conn.close()
        if self.socket:
            self.socket.close()
        self.is_receiving = False

    def cleanup(self):
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            self.is_receiving = False
        except:
            pass
