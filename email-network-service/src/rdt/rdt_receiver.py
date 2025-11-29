# Path: src/rdt/rdt_receiver.py
import socket
from common.logger import get_class_logger
from rdt.rdt_config import RDT_RECV_BUFSIZE
from rdt.rdt_packet import make_ack_packet, unpack_and_validate


class RDTReceiver:
    """
    RDT 3.0 (Stop-and-Wait) Receiver over UDP.
    """

    def __init__(self, listen_host: str, listen_port: int):
        self.log = get_class_logger(self)

        # UDP Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((listen_host, listen_port))

        # RDT 3.0 State: The sequence number we are waiting for (starts at 0)
        self.expected_seq = 0
        self.running = True
        self.log.info(f"RDTReceiver listening on {listen_host}:{listen_port}")

    def start_receiving(self):
        """
        Generator that continuously listens for packets.
        Yields valid, in-order data chunks to the application layer.
        """
        self.log.info(f"Receiver: Waiting for packet SEQ {self.expected_seq} from below.")

        while self.running:
            try:
                # rdt_rcv(rcvpkt) from wire
                rcv_bytes, sender_addr = self.sock.recvfrom(RDT_RECV_BUFSIZE)
                self.log.debug(f"Received {len(rcv_bytes)} bytes from {sender_addr}")
                rcvpkt = unpack_and_validate(rcv_bytes)

                # Event: corrupt(rcvpkt) OR has_seq(rcvpkt, wrong_seq)
                if rcvpkt is None or not rcvpkt["is_ack"] and rcvpkt["seq"] != self.expected_seq:
                    # Action: sndpkt = make_pkt(ACK, last_correct_seq, checksum); udt_send(sndpkt)
                    # The last correct seq is 1 minus current expected (toggling 0/1)
                    last_correct_seq = 1 - self.expected_seq
                    self.log.debug(
                        f"Receiver: Got corrupt or duplicate packet. Re-sending ACK {last_correct_seq} to {sender_addr}"
                    )
                    sndpkt = make_ack_packet(last_correct_seq)
                    self.sock.sendto(sndpkt, sender_addr)
                    # State remains the same: Wait for expected_seq
                    continue

                # Event: notcorrupt(rcvpkt) && has_seq(rcvpkt, expected_seq)
                if not rcvpkt["is_ack"] and rcvpkt["seq"] == self.expected_seq:
                    self.log.debug(
                        f"Receiver: Received expected SEQ {self.expected_seq}. Delivering data."
                    )

                    # Action: extract(rcvpkt, data), deliver_data(data)
                    yield rcvpkt["data"]

                    self.log.debug(f"Sending ACK {self.expected_seq} to {sender_addr}")
                    sndpkt = make_ack_packet(self.expected_seq)
                    self.sock.sendto(sndpkt, sender_addr)

                    # Action: Transition state to wait for next seq
                    self.expected_seq = 1 - self.expected_seq
                    self.log.info(
                        f"Receiver: Transitioned state. Now waiting for SEQ {self.expected_seq}."
                    )

            except Exception as e:
                self.log.exception("Receiver error:")
                if not self.running:
                    break  # Allow clean exit if stopped

    def stop(self):
        """Stops the receiving loop and closes socket."""
        self.running = False
        self.sock.close()
        self.log.info("RDTReceiver stopped.")
