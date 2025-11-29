import socket
from typing import Dict, Tuple, Optional, TYPE_CHECKING
from src.common.logger import get_class_logger
from src.rdt.rdt_packet import make_ack_packet

if TYPE_CHECKING:
    from src.rdt.rdt_dispatcher import RDTDispatcher


class RDTReceiver:
    """
    RDT 3.0 Receiver.
    Refactored to pull data from RDTDispatcher's queue and track state per client.
    """

    def __init__(
        self,
        dispatcher: "RDTDispatcher",
        yield_addr: bool = False,
    ):
        self.log = get_class_logger(self)
        self.dispatcher = dispatcher
        self.yield_addr = yield_addr
        self.sock = dispatcher.sock

        if not self.dispatcher.running:
            self.dispatcher.start()

        # RDT 3.0 State: Dictionary to track expected SEQ per client
        self.expected_seqs: Dict[Tuple[str, int], int] = {}
        self.running = True

    def start_receiving(self):
        """
        Generator that yields valid data chunks.
        """
        self.log.info("Receiver: Listening for incoming packets...")

        while self.running:
            queue_item = self.dispatcher.get_data_packet(timeout=1.0)

            if queue_item is None:
                continue

            rcvpkt, sender_addr = queue_item

            expected = self.expected_seqs.get(sender_addr, 0)

            if rcvpkt["seq"] != expected:
                last_correct_seq = 1 - expected
                self.log.debug(
                    f"Receiver: Unexpected SEQ {rcvpkt['seq']} from {sender_addr}. Expected {expected}. Resending ACK {last_correct_seq}."
                )
                sndpkt = make_ack_packet(last_correct_seq)
                self.sock.sendto(sndpkt, sender_addr)
                continue

            self.log.debug(f"Receiver: Accepted SEQ {expected} from {sender_addr}.")

            sndpkt = make_ack_packet(expected)
            self.sock.sendto(sndpkt, sender_addr)

            if self.yield_addr:
                yield rcvpkt["data"], sender_addr
            else:
                yield rcvpkt["data"]

            self.expected_seqs[sender_addr] = 1 - expected

    def reset_state(self, addr: Tuple[str, int]):
        """
        Resets the sequence number state for a specific client address.
        Call this when a client sends QUIT.
        """
        if addr in self.expected_seqs:
            self.log.info(f"Resetting RDT state for {addr}")
            del self.expected_seqs[addr]

    def stop(self):
        self.running = False
