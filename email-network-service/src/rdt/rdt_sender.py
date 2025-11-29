import socket
import threading
from src.common.logger import get_class_logger
from .rdt_config import RDT_TIMEOUT
from .rdt_packet import make_data_packet

# Import the Dispatcher type for type hinting (avoid circular import at runtime if needed)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rdt.rdt_dispatcher import RDTDispatcher


class RDTSender:
    """
    RDT 3.0 Sender.
    Refactored to use RDTDispatcher for ACK handling to prevent socket monopolization.
    """

    def __init__(self, dest_host: str, dest_port: int, dispatcher: "RDTDispatcher"):
        self.log = get_class_logger(self)
        self.dest_addr = (dest_host, dest_port)
        self.dispatcher = dispatcher

        # Ensure dispatcher is running
        if not self.dispatcher.running:
            self.dispatcher.start()

        self.curr_seq = 0
        self.log.info(f"RDTSender initialized targeting {self.dest_addr}")

    def send(self, data_chunk: bytes):
        """
        Reliable send. Blocks until ACK is received or max retries exhausted.
        """
        sndpkt = make_data_packet(self.curr_seq, data_chunk)

        max_retries = 5
        attempts = 0

        while attempts < max_retries:
            # 1. Register intent to wait for ACK *before* sending to avoid race condition
            ack_event = self.dispatcher.register_ack_waiter(
                self.dest_addr[0], self.dest_addr[1], self.curr_seq
            )

            try:
                # 2. Send the packet
                self.log.debug(f"Sender: Sending SEQ {self.curr_seq} (Attempt {attempts + 1})")
                self.dispatcher.sock.sendto(sndpkt, self.dest_addr)

                # 3. Wait for the Dispatcher to signal that the ACK arrived
                if ack_event.wait(timeout=RDT_TIMEOUT):
                    self.log.debug(f"Sender: ACK {self.curr_seq} received.")
                    self.curr_seq = 1 - self.curr_seq
                    return True  # Success
                else:
                    self.log.info(f"Sender: Timeout waiting for ACK {self.curr_seq}.")
                    attempts += 1

            finally:
                # Clean up the listener from the dispatcher
                self.dispatcher.unregister_ack_waiter(
                    self.dest_addr[0], self.dest_addr[1], self.curr_seq
                )

        self.log.error(f"Sender: Max retries ({max_retries}) reached. Connection lost.")
        raise ConnectionError("Max retries reached")

    def close(self):
        # Dispatcher is shared, so we don't stop it here usually
        pass
