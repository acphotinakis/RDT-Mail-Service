import os
import json
import threading
from typing import Optional, Dict
from src.config import Config
from src.common.logger import *
from src.auth.user import User


class UserManager:
    """
    Singleton-like manager responsible for user lifecycle: loading, saving,
    creating, and authenticating users against the persistent store (users.json).
    """

    _instance = None
    # Re-entrant lock for thread safety across server threads
    _lock = threading.RLock()

    def __new__(cls):
        # Ensure only one instance of UserManager exists in the application
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    log_debug_detailed("Creating new UserManager instance")
                    cls._instance = super(UserManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the manager and loads users from disk."""

        # In-memory cache of User objects: {username_str: User_obj}
        self.users: Dict[str, User] = {}
        self.db_file = Config.USER_DB_FILE
        self._load_users()
        log_info_detailed(f"UserManager initialized. Loaded {len(self.users)} users.")
        log_info_detailed(self.to_string())

    def _load_users(self):
        """Reads the users.json file and populates the in-memory cache."""
        with self._lock:
            # if not os.path.exists(self.db_file):
            #     log_info_detailed("No user database found. Starting fresh.")
            #     os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            #     log_debug_detailed(f"Created directory {os.path.dirname(self.db_file)}")
            #     self._save_users()  # Initialize empty file
            #     return

            try:
                log_debug_detailed(f"Loading users from {self.db_file}")
                with open(self.db_file, "r") as f:
                    data = json.load(f)
                    users_list = data.get("users", [])
                    if not isinstance(users_list, list):
                        raise ValueError("Invalid users.json format (users is not a list)")
                    for user_data in users_list:
                        try:
                            user = User.from_dict(user_data)
                            self.users[user.username] = user
                            log_debug_detailed(f"Loaded user: {user.username}")
                        except ValueError as e:
                            log_warning_detailed(f"Skipping invalid user record: {e}")
            except (json.JSONDecodeError, IOError, ValueError) as e:
                log_error_detailed(f"Failed to load user database: {e}")

    def _save_users(self):
        """Persists current users to users.json using list format."""
        with self._lock:
            try:
                log_debug_detailed("Saving user database.")

                # Convert user cache → list
                users_list = [u.to_dict() for u in self.users.values()]

                tmp_file = f"{self.db_file}.tmp"
                with open(tmp_file, "w") as f:
                    json.dump({"users": users_list}, f, indent=2)

                os.replace(tmp_file, self.db_file)
                log_debug_detailed("User database saved successfully.")
            except IOError as e:
                log_error_detailed(f"Failed to save user database: {e}")

    def get_user(self, username: str) -> Optional[User]:
        """Retrieves a User object by username (case-insensitive)."""
        with self._lock:
            log_debug_detailed(f"Attempting to get user: {username}")
            user = self.users.get(username.lower())
            if user:
                log_debug_detailed(f"User found: {username}")
            else:
                log_debug_detailed(f"User not found: {username}")
            return user

    def create_user(self, username: str, password: str) -> User:
        """Creates a new user, hashes their password, saves to disk, and initializes mailbox."""
        with self._lock:
            lower_name = username.lower()
            if lower_name in self.users:
                log_warning_detailed(f"Attempted to create existing user: {username}")
                raise ValueError(f"User '{username}' already exists.")

            log_debug_detailed(f"Creating new user: {username}")
            new_user = User(lower_name, password)
            self.users[lower_name] = new_user

            # 1. Persist user credentials
            self._save_users()

            # 2. Initialize physical mailbox directory
            try:
                log_debug_detailed(
                    f"Creating mailbox directory for {username} at {new_user.mailbox_path}"
                )
                os.makedirs(new_user.mailbox_path, exist_ok=True)
                # Create initial empty metadata file for the Mailbox subsystem
                metadata_path = os.path.join(new_user.mailbox_path, "metadata.json")
                if not os.path.exists(metadata_path):
                    log_debug_detailed(f"Creating metadata file for {username} at {metadata_path}")
                    with open(metadata_path, "w") as f:
                        json.dump({"messages": {}}, f)
            except OSError as e:
                log_error_detailed(f"Failed to create mailbox directory for {username}: {e}")
                # Note: In a production system, you might roll back user creation here.

            log_info_detailed(f"Created new user: {username}")
            return new_user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Attempts to authenticate a user. Returns User object on success, None on failure."""
        log_debug_detailed(f"Attempting to authenticate user: {username}")
        # No lock needed here, get_user handles read locking, verify_password doesn't modify state
        user = self.get_user(username)
        if user and user.verify_password(password):
            log_debug_detailed(f"Authentication successful for: {username}")
            return user
        log_warning_detailed(f"Authentication failed for: {username}")
        return None

    def to_string(self) -> str:
        """
        Returns a detailed diagnostic overview of the UserManager,
        including cache state, database file details, and locking info.
        """

        props = {
            "DB File": self.db_file,
            "Users Loaded": len(self.users),
            "Usernames": ", ".join(self.users.keys()) if self.users else "(none)",
            "Lock Type": type(self._lock).__name__,
            "Singleton Instance": hex(id(self)),
        }

        longest = max(len(k) for k in props.keys())
        lines = ["\nUserManager State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)
