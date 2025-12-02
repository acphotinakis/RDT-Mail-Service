from src.auth.user_manager import UserManager
from src.auth.user import User
from typing import Optional, Dict
from src.common.logger import *


class AuthController:
    """
    Simple controller that wraps your UserManager (or server auth).
    """

    def __init__(self):

        self.user_manager = UserManager()
        log_info_detailed("AuthController initialized.")

    def login(self, username: str, password: str) -> Optional[bool]:
        log_info_detailed(f"Attempting login for user: {username}")
        user = self.user_manager.get_user(username)
        if not user:
            log_warning_detailed(f"Login failed: User '{username}' not found.")
            return None  # User not found

        if user.verify_password(password):
            log_info_detailed(f"Login successful for user: {username}")
            return True  # Success
        else:
            log_warning_detailed(f"Login failed: Invalid password for user: {username}")
            return False  # Wrong password

    def user_exists(self, username: str) -> bool:
        log_debug_detailed(f"Checking if user exists: {username}")
        exists = self.user_manager.get_user(username) is not None
        log_debug_detailed(f"User '{username}' exists: {exists}")
        return exists

    def signup(self, username: str, password: str) -> Optional[User]:
        log_info_detailed(f"Attempting signup for new user: {username}")
        if self.user_manager.get_user(username):
            log_warning_detailed(f"Signup failed: User '{username}' already exists.")
            return None
        new_user = self.user_manager.create_user(username, password)
        if new_user:
            log_info_detailed(f"Signup successful for new user: {username}")
        else:
            log_error_detailed(f"Signup failed for user: {username} during creation.")
        return new_user
