import socket
import threading
from src.common.logger import *
from src.rdt.rdt_packet import make_data_packet
from src.config import Config

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

        self.dest_addr = (dest_host, dest_port)
        self.dispatcher = dispatcher

        # Ensure dispatcher is running
        if not self.dispatcher.running:
            self.dispatcher.start()

        self.curr_seq = 0
        log_info_detailed(f"RDT Sender initialized on {self.dest_addr}")
        log_info_detailed(self.to_string())

    def send(self, data_chunk: bytes):
        """
        Reliable send. Blocks until ACK is received or max retries exhausted.
        """

        sndpkt = make_data_packet(self.curr_seq, data_chunk)

        max_retries = 5
        attempts = 0

        while attempts < max_retries:
            seq_to_use = self.curr_seq

            # 1. Register intent to wait for ACK *before* sending to avoid race condition
            ack_event = self.dispatcher.register_ack_waiter(
                self.dest_addr[0], self.dest_addr[1], seq_to_use
            )

            try:
                log_debug_detailed(f"Sender: Sending SEQ {seq_to_use} (Attempt {attempts + 1})")
                self.dispatcher.sock.sendto(sndpkt, self.dest_addr)

                if ack_event.wait(timeout=Config.RDT_TIMEOUT):
                    log_debug_detailed(f"Sender: ACK {seq_to_use} received.")
                    # Only toggle state after success logic is confirmed
                    self.curr_seq = 1 - self.curr_seq
                    return True
                else:
                    log_info_detailed(f"Sender: Timeout waiting for ACK {seq_to_use}.")
                    attempts += 1

            finally:
                # Unregister the specific sequence we waited for
                self.dispatcher.unregister_ack_waiter(
                    self.dest_addr[0], self.dest_addr[1], seq_to_use
                )

        log_error_detailed(f"Sender: Max retries ({max_retries}) reached. Connection lost.")
        raise ConnectionError("Max retries reached")

    def close(self):
        # Dispatcher is shared, so we don't stop it here usually
        pass

    def to_string(self) -> str:
        """
        Returns a diagnostic summary of the sender's connection state.
        """
        props = {
            "Destination": f"{self.dest_addr[0]}:{self.dest_addr[1]}",
            "Current SEQ": self.curr_seq,
            "Dispatcher Running": self.dispatcher.running,
            "Socket FD": self.dispatcher.sock.fileno(),
        }

        longest = max(len(k) for k in props)
        lines = ["\nRDTSender State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
