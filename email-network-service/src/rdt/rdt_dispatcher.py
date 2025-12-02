import threading
import queue
import socket

from typing import Dict, Tuple, Optional
from src.rdt.rdt_packet import unpack_and_validate
from src.config import Config
from src.common.logger import *


class RDTDispatcher:
    """
    The Central Nervous System for the RDT protocol.

    It owns the UDP socket and runs a background thread to continuously
    receive packets. It inspects every packet and routes it:
    1. ACK Packets -> Routed to the specific RDTSender waiting for them.
    2. Data Packets -> Pushed to a Queue for the RDTReceiver to consume.
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.sock.settimeout(1.0)
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # Queue for Application Data (consumed by RDTReceiver)
        # Stores tuples: (packet_dict, source_address)
        self.data_queue = queue.Queue()

        # Dictionary for routing ACKs
        # Key: (remote_ip, remote_port, sequence_number)
        # Value: threading.Event()
        self._ack_listeners: Dict[Tuple[str, int, int], threading.Event] = {}
        self._ack_lock = threading.Lock()

        log_info_detailed("RDT Dispatcher initialized.")
        log_info_detailed(self.to_string())

    def start(self):
        """Starts the background listening thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._listen_loop, name="RDT-Dispatcher", daemon=True
        )
        self._thread.start()
        log_info_detailed("RDT Dispatcher thread started.")

    def stop(self):
        """Stops the background thread."""
        self.running = False
        # We do not close the socket here, as it might be owned by the application
        if self._thread:
            self._thread.join(timeout=1.0)
        log_info_detailed("RDT Dispatcher stopped.")

    def _listen_loop(self):
        """
        The ONLY place in the entire application that calls sock.recvfrom().
        """
        while self.running:
            try:
                # 1. Block waiting for any packet
                raw_bytes, addr = self.sock.recvfrom(Config.RDT_RECV_BUFSIZE)

                # 2. Deserialize and Validate
                packet = unpack_and_validate(raw_bytes)

                if packet is None:
                    # Corrupt packet, ignore
                    continue

                # 3. Route the packet
                if packet["is_ack"]:
                    self._handle_ack(packet, addr)
                else:
                    self._handle_data(packet, addr)

            except socket.timeout:
                continue  # Normal if socket has a timeout set
            except OSError:
                if self.running:
                    log_error_detailed("Socket closed unexpectedly.")
                break
            except Exception as e:
                log_error_detailed(f"Dispatcher error: {e}")

    def _handle_ack(self, packet, addr):
        """Fires the event if a Sender is waiting for this specific ACK."""
        seq = packet["seq"]
        key = (addr[0], addr[1], seq)

        with self._ack_lock:
            if key in self._ack_listeners:
                event = self._ack_listeners[key]
                event.set()  # Wake up the waiting Sender
                # We don't remove it here; the Sender removes it after waking up.

    def _handle_data(self, packet, addr):
        """Pushes data to the queue for the Receiver."""
        # Store (packet_dict, address)
        self.data_queue.put((packet, addr))

    # --- Methods for RDTSender ---
    def register_ack_waiter(self, host: str, port: int, seq: int) -> threading.Event:
        """Called by Sender BEFORE sending data."""
        key = (host, port, seq)
        event = threading.Event()
        with self._ack_lock:
            self._ack_listeners[key] = event
        return event

    def unregister_ack_waiter(self, host: str, port: int, seq: int):
        """Called by Sender after receiving ACK or timeout."""
        key = (host, port, seq)
        with self._ack_lock:
            if key in self._ack_listeners:
                del self._ack_listeners[key]

    # --- Methods for RDTReceiver ---
    def get_data_packet(self, timeout=None) -> Optional[Tuple[Dict, Tuple[str, int]]]:
        """Blocking call to get the next valid data packet."""
        try:
            return self.data_queue.get(block=True, timeout=timeout)
        except queue.Empty:
            return None

    def to_string(self) -> str:
        """
        Returns a detailed snapshot of dispatcher runtime state.
        """
        thread_alive = self._thread.is_alive() if self._thread else False

        props = {
            "Socket FD": self.sock.fileno(),
            "Socket Timeout": self.sock.gettimeout(),
            "Dispatcher Running": self.running,
            "Thread Alive": thread_alive,
            "Thread Name": self._thread.name if self._thread else None,
            "Queued Data Packets": self.data_queue.qsize(),
            "ACK Listeners Count": len(self._ack_listeners),
        }

        longest = max(len(k) for k in props)
        lines = ["\nRDTDispatcher State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
