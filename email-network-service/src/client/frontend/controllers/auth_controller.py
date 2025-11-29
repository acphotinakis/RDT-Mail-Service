from src.auth.user_manager import UserManager
from src.auth.user import User
from typing import Optional, Dict
from src.common.logger import get_class_logger


class AuthController:
    """
    Simple controller that wraps your UserManager (or server auth).
    """

    def __init__(self):
        self.log = get_class_logger(self)
        self.user_manager = UserManager()
        self.log.info("AuthController initialized.")

    def login(self, username: str, password: str) -> Optional[bool]:
        self.log.info(f"Attempting login for user: {username}")
        user = self.user_manager.get_user(username)
        if not user:
            self.log.warning(f"Login failed: User '{username}' not found.")
            return None  # User not found

        if user.verify_password(password):
            self.log.info(f"Login successful for user: {username}")
            return True  # Success
        else:
            self.log.warning(f"Login failed: Invalid password for user: {username}")
            return False  # Wrong password

    def user_exists(self, username: str) -> bool:
        self.log.debug(f"Checking if user exists: {username}")
        exists = self.user_manager.get_user(username) is not None
        self.log.debug(f"User '{username}' exists: {exists}")
        return exists

    def signup(self, username: str, password: str) -> Optional[User]:
        self.log.info(f"Attempting signup for new user: {username}")
        if self.user_manager.get_user(username):
            self.log.warning(f"Signup failed: User '{username}' already exists.")
            return None
        new_user = self.user_manager.create_user(username, password)
        if new_user:
            self.log.info(f"Signup successful for new user: {username}")
        else:
            self.log.error(f"Signup failed for user: {username} during creation.")
        return new_user
