import pytest
import os
import json
from src.auth.user_manager import UserManager
from src.common.config import USER_DB_FILE, MAILBOXES_DIR


@pytest.fixture(autouse=True)
def cleanup_user_db():
    """Fixture to automatically clean up the user database before and after each test."""
    # Before the test
    if os.path.exists(USER_DB_FILE):
        os.remove(USER_DB_FILE)

    yield

    # After the test
    if os.path.exists(USER_DB_FILE):
        os.remove(USER_DB_FILE)


def test_usermanager_singleton():
    """Tests that UserManager is a singleton."""
    um1 = UserManager()
    um2 = UserManager()
    assert um1 is um2


def test_create_user():
    """Tests creating a new user."""
    um = UserManager()
    user = um.create_user("newuser", "password123")

    assert user is not None
    assert user.username == "newuser"

    # Check if user is in memory
    assert um.get_user("newuser") is not None

    # Check if user is in the database file
    with open(USER_DB_FILE, "r") as f:
        data = json.load(f)
        assert "newuser" in data

    # Check if mailbox directory was created
    assert os.path.exists(os.path.join(MAILBOXES_DIR, "newuser"))


def test_create_existing_user():
    """Tests that creating a user that already exists raises an error."""
    um = UserManager()
    um.create_user("existinguser", "password123")

    with pytest.raises(ValueError):
        um.create_user("existinguser", "anotherpassword")


def test_authenticate_user():
    """Tests user authentication."""
    um = UserManager()
    um.create_user("authuser", "securepassword")

    # Test successful authentication
    authenticated_user = um.authenticate("authuser", "securepassword")
    assert authenticated_user is not None
    assert authenticated_user.username == "authuser"

    # Test failed authentication
    failed_user = um.authenticate("authuser", "wrongpassword")
    assert failed_user is None


def test_get_nonexistent_user():
    """Tests that getting a non-existent user returns None."""
    um = UserManager()
    user = um.get_user("nosuchuser")
    assert user is None
