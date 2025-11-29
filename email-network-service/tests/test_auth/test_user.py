import pytest
from src.auth.user import User


def test_user_creation():
    """Tests basic user object creation."""
    user = User("testuser")
    assert user.username == "testuser"
    assert user.password_hash is None
    assert "testuser" in user.mailbox_path


def test_set_and_verify_password():
    """Tests that a password can be set and correctly verified."""
    user = User("testuser")
    user.set_password("password123")
    assert user.password_hash is not None
    assert user.verify_password("password123") is True
    assert user.verify_password("wrongpassword") is False


def test_to_and_from_dict():
    """Tests serialization and deserialization of the User object."""
    user = User("testuser")
    user.set_password("password123")
    user_dict = user.to_dict()

    assert user_dict["username"] == "testuser"
    assert user_dict["password_hash"] is not None

    new_user = User.from_dict(user_dict)
    assert new_user.username == "testuser"
    assert new_user.password_hash == user.password_hash
    assert new_user.verify_password("password123") is True
