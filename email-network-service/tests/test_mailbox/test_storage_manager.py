import pytest
import os
from mailbox.storage_manager import StorageManager
from auth.user import User
from client.frontend.models import EmailData
from email.message import Message

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_storage_manager():
    print("\n=== RESETTING StorageManager Singleton ===")
    StorageManager._instance = None
    print("StorageManager._instance set to None\n")


@pytest.fixture
def storage_manager():
    print("\n=== Creating NEW StorageManager instance ===")
    sm = StorageManager()
    print(f"StorageManager instance created: {sm}\n")
    return sm


@pytest.fixture
def test_user():
    print("\n=== Creating Test User ===")
    user = User("testuser")
    print(f"User.username = {user.username}")
    print(f"User.mailbox_path = {user.mailbox_path}\n")
    return user


# ============================================================================
# TEST 1 — SAVE + LIST + RETRIEVE EMAIL
# ============================================================================


def test_save_and_list_email(storage_manager, test_user):
    print("\n==================== TEST: SAVE AND LIST EMAIL ====================\n")

    # Build MIME email
    msg = Message("This is a test email.")
    msg["Subject"] = "Test Email"
    msg["From"] = "sender@example.com"
    msg["To"] = "testuser@example.com"

    print("Raw MIME constructed:")
    print(msg.as_string())

    email_data = EmailData(
        raw_message=msg,
        uid="123",
        subject="Test Email",
        sender="sender@example.com",
        recipient="testuser@example.com",
        date="now",
    )

    print("\nCalling storage_manager.save_email()...")
    saved_path = storage_manager.save_email(test_user, email_data)
    print(f"save_email() returned path: {saved_path}")

    assert saved_path is not None, "save_email() returned None — SAVE FAILED"

    # Confirm file exists
    print(f"Checking if saved file exists: {saved_path}")
    print("Exists?", os.path.exists(saved_path))

    # List messages
    print("\nCalling storage_manager.list_messages()...")
    messages = storage_manager.list_messages(test_user)
    print(f"Messages returned: {messages}")

    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"

    filename, size, uid = messages[0]
    print(f"Extracted message tuple:\n  filename={filename}\n  size={size}\n  uid={uid}")

    assert uid == "123", f"Expected UID '123', got {uid}"

    # Retrieve content
    print("\nCalling storage_manager.get_message_content()...")
    content = storage_manager.get_message_content(test_user, filename)

    print("\nRetrieved message content:")
    print(content)

    assert content is not None, "Message content returned None"
    assert "Subject: Test Email" in content, "Subject header missing in saved message"

    print("\n==================== END TEST ====================\n")


# ============================================================================
# TEST 2 — DELETE EMAIL
# ============================================================================


def test_delete_email(storage_manager, test_user):
    print("\n======================== TEST: DELETE EMAIL ========================\n")

    msg = MIMEText("Delete me")
    msg["Subject"] = "Email to be deleted"

    print("Constructed MIME for deletion test:")
    print(msg.as_string())

    email_data = EmailData(
        raw_message=msg,
        uid="456",
        subject="Delete",
        sender="s",
        recipient="r",
        date="d",
    )

    print("\nSaving email...")
    saved_path = storage_manager.save_email(test_user, email_data)
    print(f"Saved at path: {saved_path}")

    filename = os.path.basename(saved_path)
    print(f"Extracted filename: {filename}")

    print("\nCalling storage_manager.delete_email()...")
    success = storage_manager.delete_email(test_user, filename)
    print(f"delete_email() returned: {success}")

    assert success is True, "delete_email() failed — returned False"

    print("\nCalling list_messages() after delete...")
    messages = storage_manager.list_messages(test_user)
    print(f"Messages returned after delete: {messages}")

    assert len(messages) == 0, f"Expected 0 messages, got {len(messages)}"

    print("\n==================== END DELETE TEST ====================\n")
