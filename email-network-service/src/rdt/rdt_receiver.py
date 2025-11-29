# Path: src/rdt/rdt_receiver.py
import socket
from src.common.logger import get_class_logger
from src.rdt.rdt_config import RDT_RECV_BUFSIZE
from src.rdt.rdt_packet import make_ack_packet, unpack_and_validate
from typing import Optional, Dict


class RDTReceiver:
    """
    RDT 3.0 (Stop-and-Wait) Receiver over UDP.
    Can use a socket provided by its owner or create its own.
    """

    def __init__(
        self,
        listen_host: Optional[str] = None,
        listen_port: Optional[int] = None,
        sock: Optional[socket.socket] = None,
        yield_addr: bool = False,
    ):
        """
        Initializes the receiver.
        Args:
            listen_host: Host to bind to (if sock is not provided).
            listen_port: Port to bind to (if sock is not provided).
            sock: An existing socket to use.
            yield_addr: If True, yields (data, address) tuples. Otherwise, yields data only.
        """
        self.log = get_class_logger(self)
        self.yield_addr = yield_addr
        self._is_shared_socket = sock is not None

        if sock:
            self.sock = sock
            try:
                host, port = self.sock.getsockname()
                self.log.info(f"RDTReceiver initialized on existing socket {host}:{port}")
            except OSError:
                self.log.info("RDTReceiver initialized with a non-connected socket.")
        elif listen_host is not None and listen_port is not None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((listen_host, listen_port))
            self.log.info(f"RDTReceiver created and bound to {listen_host}:{listen_port}")
        else:
            raise ValueError("Must provide either a socket or a host/port pair.")

        # RDT 3.0 State
        self.expected_seq = 0
        self.running = True

    def start_receiving(self):
        """
        Generator that continuously listens for packets.
        Yields valid, in-order data chunks to the application layer.
        """
        self.log.info(f"Receiver: Waiting for packet SEQ {self.expected_seq} from below.")

        while self.running:
            try:
                rcv_bytes, sender_addr = self.sock.recvfrom(RDT_RECV_BUFSIZE)
                self.log.debug(f"Received {len(rcv_bytes)} bytes from {sender_addr}")
                rcvpkt = unpack_and_validate(rcv_bytes)

                if rcvpkt is None or (not rcvpkt["is_ack"] and rcvpkt["seq"] != self.expected_seq):
                    last_correct_seq = 1 - self.expected_seq
                    self.log.debug(
                        f"Receiver: Got corrupt/duplicate. Re-sending ACK {last_correct_seq} to {sender_addr}"
                    )
                    sndpkt = make_ack_packet(last_correct_seq)
                    self.sock.sendto(sndpkt, sender_addr)
                    continue

                if not rcvpkt["is_ack"] and rcvpkt["seq"] == self.expected_seq:
                    self.log.debug(
                        f"Receiver: Received expected SEQ {self.expected_seq}. Delivering data."
                    )

                    # Yield data, optionally with address
                    if self.yield_addr:
                        yield rcvpkt["data"], sender_addr
                    else:
                        yield rcvpkt["data"]

                    self.log.debug(f"Sending ACK {self.expected_seq} to {sender_addr}")
                    sndpkt = make_ack_packet(self.expected_seq)
                    self.sock.sendto(sndpkt, sender_addr)

                    self.expected_seq = 1 - self.expected_seq
                    self.log.info(
                        f"Receiver: Transitioned state. Now waiting for SEQ {self.expected_seq}."
                    )

            except Exception:
                if not self.running:
                    self.log.info("Receiver loop gracefully shutting down.")
                    break
                self.log.exception("Receiver error:")

    def stop(self):
        """Stops the receiving loop. Closes the socket only if it created it."""
        self.running = False
        if not self._is_shared_socket:
            self.sock.close()
            self.log.info("RDTReceiver stopped and closed its socket.")
        else:
            # The owner must close the shared socket to unblock recvfrom
            self.log.info("RDTReceiver stop signal received (socket managed externally).")
