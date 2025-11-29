from src.auth.user_manager import UserManager
from src.auth.user import User
from typing import Optional, Dict


class AuthController:
    """
    Simple controller that wraps your UserManager (or server auth).
    """

    def __init__(self):
        self.user_manager = UserManager()

    def login(self, username: str, password: str) -> Optional[bool]:
        user = self.user_manager.get_user(username)
        if not user:
            return None  # User not found
        
        if user.verify_password(password):
            return True  # Success
        else:
            return False # Wrong password

    def user_exists(self, username: str) -> bool:
        return self.user_manager.get_user(username) is not None

    def signup(self, username: str, password: str) -> Optional[User]:
        if self.user_manager.get_user(username):
            return None
        return self.user_manager.create_user(username, password)
