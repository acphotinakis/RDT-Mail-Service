import pytest
from threading import Thread
from time import sleep

from src.smtp.smtp_server import SMTPServer
from src.smtp.smtp_client import SMTPClient
from src.common.config import SMTP_SERVER_HOST, SMTP_SERVER_PORT
from src.auth.user_manager import UserManager
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User

@pytest.fixture(scope="module")
def server():
    """Fixture to start and stop the SMTP server."""
    UserManager().create_user("testuser", "password")
    
    server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    sleep(1) # Give the server time to start
    yield
    server.stop()

def test_smtp_integration(server):
    """A full integration test for the SMTP protocol."""
    client = SMTPClient()
    
    sender = "sender@test.com"
    recipient = "testuser@localhost"
    subject = "Integration Test"
    body = "This is an integration test email."
    
    sent = client.send_email(sender, recipient, subject, body)
    
    assert sent is True
    
    # Check if the email was saved in the recipient's mailbox
    storage = StorageManager()
    messages = storage.list_messages(User("testuser"))
    assert len(messages) > 0
    
    filename = messages[0][0]
    content = storage.get_message_content(User("testuser"), filename)
    assert subject in content
    assert body in content
