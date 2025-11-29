import pytest
from threading import Thread
from time import sleep

from rdt.rdt_sender import RDTSender
from rdt.rdt_receiver import RDTReceiver
from common.config import RDT_TIMEOUT

HOST = "127.0.0.1"
SENDER_PORT = 9000
RECEIVER_PORT = 9001


@pytest.fixture
def rdt_pair():
    """Fixture to create a sender and receiver for testing."""
    sender = RDTSender(HOST, RECEIVER_PORT)
    receiver = RDTReceiver(HOST, SENDER_PORT)
    yield sender, receiver
    sender.close()
    receiver.stop()


def test_rdt_send_receive_one_packet(rdt_pair):
    """Tests sending and receiving a single packet."""
    sender, receiver = rdt_pair

    # The receiver should listen on the sender's port
    receiver.sock.bind((HOST, SENDER_PORT))

    data_to_send = b"hello rdt"

    received_data = []

    def receive_thread():
        for data in receiver.start_receiving():
            received_data.append(data)
            break  # Stop after one packet

    recv_thread = Thread(target=receive_thread, daemon=True)
    recv_thread.start()

    # The sender should target the receiver's listening port
    sender.dest_addr = (HOST, SENDER_PORT)
    sender.send(data_to_send)

    recv_thread.join(timeout=RDT_TIMEOUT * 2)

    assert len(received_data) == 1
    assert received_data[0] == data_to_send
