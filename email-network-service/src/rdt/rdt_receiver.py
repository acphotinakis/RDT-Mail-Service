import socket
from typing import Dict, Tuple, TYPE_CHECKING
from src.common.logger import get_class_logger
from src.rdt.rdt_packet import make_ack_packet

if TYPE_CHECKING:
    from src.rdt.rdt_dispatcher import RDTDispatcher


class RDTReceiver:
    """
    RDT 3.0 Receiver.
    Standardized to ALWAYS yield (data, sender_address).
    """

    def __init__(self, dispatcher: "RDTDispatcher"):
        self.log = get_class_logger(self)
        self.dispatcher = dispatcher
        self.sock = dispatcher.sock

        if not self.dispatcher.running:
            self.dispatcher.start()

        # Track expected sequence number per client (IP, Port)
        self.expected_seqs: Dict[Tuple[str, int], int] = {}
        self.running = True

    def start_receiving(self):
        """
        Generator that yields (valid_data_bytes, sender_addr).
        """
        self.log.info("Receiver: Listening for incoming packets...")

        while self.running:
            # 1. Get next packet from Dispatcher Queue
            queue_item = self.dispatcher.get_data_packet(timeout=1.0)

            if queue_item is None:
                continue

            rcvpkt, sender_addr = queue_item

            # 2. Check Sequence Number
            expected = self.expected_seqs.get(sender_addr, 0)

            if rcvpkt["seq"] != expected:
                # Duplicate/Out-of-order: Resend ACK for the LAST correctly received packet
                last_correct_seq = 1 - expected
                self.log.debug(
                    f"Receiver: Unexpected SEQ {rcvpkt['seq']} from {sender_addr}. "
                    f"Expected {expected}. Resending ACK {last_correct_seq}."
                )
                sndpkt = make_ack_packet(last_correct_seq)
                self.sock.sendto(sndpkt, sender_addr)
                continue

            # 3. Good Packet Received
            self.log.debug(f"Receiver: Accepted SEQ {expected} from {sender_addr}.")

            # Send ACK for current packet
            sndpkt = make_ack_packet(expected)
            self.sock.sendto(sndpkt, sender_addr)

            # Update state
            self.expected_seqs[sender_addr] = 1 - expected

            # 4. Yield Data to Application
            # Always yield tuple to be consistent
            yield rcvpkt["data"], sender_addr

    def reset_state(self, addr: Tuple[str, int]):
        """Resets RDT state for a client (used on QUIT)."""
        if addr in self.expected_seqs:
            del self.expected_seqs[addr]

    def stop(self):
        self.running = False
