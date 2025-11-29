import pytest
from unittest.mock import MagicMock, patch
from pop3.pop3_client import POP3Client


@pytest.fixture
def mock_rdt():
    with (
        patch("src.pop3.pop3_client.RDTSender") as mock_sender,
        patch("src.pop3.pop3_client.RDTReceiver") as mock_receiver,
    ):
        yield mock_sender, mock_receiver


def test_pop3_client_connect(mock_rdt):
    """Tests the connect method of the POP3 client."""
    mock_sender_instance = mock_rdt[0].return_value
    mock_receiver_instance = mock_rdt[1].return_value

    # Simulate the server sending a welcome message
    def mock_start_receiving():
        yield b"+OK POP3 server ready\r\n"

    mock_receiver_instance.start_receiving.return_value = mock_start_receiving()

    client = POP3Client()
    client.connect()

    assert client.is_connected is True


def test_pop3_client_auth(mock_rdt):
    """Tests the authentication process."""
    mock_sender_instance = mock_rdt[0].return_value
    mock_receiver_instance = mock_rdt[1].return_value

    def mock_start_receiving():
        yield b"+OK POP3 server ready\r\n"
        yield b"+OK User accepted\r\n"
        yield b"+OK Mailbox open\r\n"

    mock_receiver_instance.start_receiving.return_value = mock_start_receiving()

    client = POP3Client()
    client.connect()
    client.authenticate("testuser", "password")

    # Check that USER and PASS commands were sent
    mock_sender_instance.send.assert_any_call(b"USER testuser\r\n")
    mock_sender_instance.send.assert_any_call(b"PASS password\r\n")


def test_pop3_client_fetch(mock_rdt):
    """Tests fetching emails."""
    mock_sender_instance = mock_rdt[0].return_value
    mock_receiver_instance = mock_rdt[1].return_value

    def mock_start_receiving():
        yield b"+OK POP3 server ready\r\n"  # connect
        yield b"+OK User accepted\r\n"  # auth
        yield b"+OK Mailbox open\r\n"  # auth
        yield b"+OK 1 123\r\n"  # stat
        yield b"+OK 1 messages\r\n"  # list
        yield b"1 123\r\n"
        yield b".\r\n"
        yield b"+OK 123 octets\r\n"  # retr
        yield b"From: sender\r\n\r\nBody\r\n"
        yield b".\r\n"
        yield b"+OK message deleted\r\n"  # dele
        yield b"+OK goodbye\r\n"  # quit

    mock_receiver_instance.start_receiving.return_value = mock_start_receiving()

    client = POP3Client()
    emails = client.fetch_new_emails("testuser", "password")

    assert len(emails) == 1
    assert "From: sender" in emails[0]
