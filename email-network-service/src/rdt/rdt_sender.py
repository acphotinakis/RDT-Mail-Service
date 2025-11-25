# Path: src/rdt/rdt_sender.py
import socket
from src.common.logger import get_class_logger
from src.rdt.rdt_config import RDT_TIMEOUT, RDT_RECV_BUFSIZE
from .rdt_packet import make_data_packet, unpack_and_validate


class RDTSender:
    """
    RDT 3.0 (Stop-and-Wait) Sender over UDP.
    """

    def __init__(self, dest_host: str, dest_port: int):
        self.log = get_class_logger(self)
        self.dest_addr = (dest_host, dest_port)

        # UDP Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # The socket timeout serves as the RDT retransmission timer
        self.sock.settimeout(RDT_TIMEOUT)

        # RDT 3.0 State: The sequence number next to be sent (starts at 0)
        self.curr_seq = 0
        self.log.info(f"RDTSender initialized targeting {self.dest_addr}")

    def send(self, data_chunk: bytes):
        """
        Blocking call to send one chunk of data reliably.
        Returns only when the chunk is successfully acknowledged by the receiver.
        """
        # Create the packet for the current sequence number
        sndpkt = make_data_packet(self.curr_seq, data_chunk)
        self.log.debug(
            f"Sender: Attempting to send packet SEQ {self.curr_seq} ({len(data_chunk)} bytes)"
        )

        # State: Waiting for ACK for curr_seq
        while True:
            try:
                # Action: udt_send(sndpkt) and effectively start_timer (via socket timeout)
                self.sock.sendto(sndpkt, self.dest_addr)

                # Try to receive ACK
                rcv_bytes, _ = self.sock.recvfrom(RDT_RECV_BUFSIZE)
                rcvpkt = unpack_and_validate(rcv_bytes)

                if rcvpkt is None:
                    # Event: corrupt(rcvpkt). Action: Do nothing, wait for timeout.
                    self.log.warning(
                        "Sender: Received corrupt packet while waiting for ACK. Ignoring."
                    )
                    continue

                if rcvpkt["is_ack"] and rcvpkt["seq"] == self.curr_seq:
                    # Event: notcorrupt(rcvpkt) && isACK(rcvpkt, curr_seq)
                    # Action: stop_timer (happens by exiting loop), transition state.
                    self.log.debug(
                        f"Sender: Received correct ACK {self.curr_seq}. Transitioning state."
                    )
                    # Toggle sequence number between 0 and 1 for the next call
                    self.curr_seq = 1 - self.curr_seq
                    return  # Exit blocks, ready for next call from above
                else:
                    # Event: isACK(rcvpkt, wrong_seq). Action: Do nothing.
                    self.log.debug(
                        f"Sender: Received wrong ACK {rcvpkt.get('seq')}. Ignoring."
                    )
                    continue

            except socket.timeout:
                # Event: timeout. Action: udt_send(sndpkt), start_timer
                self.log.info(
                    f"Sender: Timeout waiting for ACK {self.curr_seq}. Retransmitting."
                )
                # Loop continues, triggering retransmission at top of loop
                continue
            except Exception as e:
                self.log.error(f"Sender: Unexpected socket error: {e}")
                raise e

    def close(self):
        """Closes the UDP socket."""
        self.sock.close()
        self.log.info("RDTSender closed.")
