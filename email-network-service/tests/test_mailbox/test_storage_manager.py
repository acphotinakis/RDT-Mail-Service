import pytest
import os
from src.mailbox.storage_manager import StorageManager
from src.auth.user import User
from src.client.frontend.models import EmailData
from email.message import Message

@pytest.fixture
def storage_manager():
    """Fixture to provide a clean StorageManager instance for each test."""
    # This will create a new instance for each test
    return StorageManager()

@pytest.fixture
def test_user():
    """Fixture to provide a test user."""
    return User("testuser")

def test_save_and_list_email(storage_manager, test_user):
    """Tests saving and listing an email."""
    msg = Message()
    msg["From"] = "sender@example.com"
    msg["To"] = "testuser@example.com"
    msg["Subject"] = "Test Email"
    msg.set_payload("This is a test email.")
    
    email_data = EmailData(
        raw_message=msg,
        uid="123",
        subject="Test Email",
        sender="sender@example.com",
        recipient="testuser@example.com",
        date="some_date",
    )
    
    # Save the email
    saved_path = storage_manager.save_email(test_user, email_data)
    assert saved_path is not None
    
    # List messages
    messages = storage_manager.list_messages(test_user)
    assert len(messages) == 1
    filename, size, uid = messages[0]
    assert uid == "123"
    
    # Get content
    content = storage_manager.get_message_content(test_user, filename)
    assert content is not None
    assert "Subject: Test Email" in content
    
    # cleanup
    os.remove(saved_path)

def test_delete_email(storage_manager, test_user):
    """Tests deleting an email."""
    msg = Message()
    msg["Subject"] = "Email to be deleted"
    email_data = EmailData(raw_message=msg, uid="456", subject="Delete", sender="s", recipient="r", date="d")
    
    # Save the email
    saved_path = storage_manager.save_email(test_user, email_data)
    filename = os.path.basename(saved_path)
    
    # Delete the email
    success = storage_manager.delete_email(test_user, filename)
    assert success is True
    
    # List messages and verify it's gone
    messages = storage_manager.list_messages(test_user)
    assert len(messages) == 0
    
    # cleanup
    os.remove(saved_path)
