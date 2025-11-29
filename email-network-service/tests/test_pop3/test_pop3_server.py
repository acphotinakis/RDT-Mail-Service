import pytest
from threading import Thread
from time import sleep

from pop3.pop3_server import POP3Server
from pop3.pop3_client import POP3Client
from common.config import POP3_SERVER_HOST, POP3_SERVER_PORT, CLIENT_IP, CLIENT_LISTENING_PORT
from auth.user_manager import UserManager
from mailbox.storage_manager import StorageManager
from auth.user import User
from client.frontend.models import EmailData
from email.message import Message


@pytest.fixture(scope="module")
def server():
    """Fixture to start and stop the POP3 server."""
    # Setup: create a user and an email
    UserManager().create_user("testuser", "password")
    msg = Message()
    msg["From"] = "sender@test.com"
    msg["To"] = "testuser@test.com"
    msg["Subject"] = "Test"
    msg.set_payload("This is a test.")
    email_data = EmailData(
        raw_message=msg, uid="testuid", subject="Test", sender="f", recipient="t", date="d"
    )
    StorageManager().save_email(User("testuser"), email_data)

    server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)
    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    sleep(1)  # Give the server time to start
    yield
    server.stop()


def test_pop3_integration(server):
    """A full integration test for the POP3 protocol."""
    client = POP3Client()
    client.connect()
    client.authenticate("testuser", "password")

    count, size = client.stat()
    assert count == 1

    messages = client.list()
    assert len(messages) == 1

    email_content = client.retr(1)
    assert "Subject: Test" in email_content

    client.dele(1)
    client.quit()
