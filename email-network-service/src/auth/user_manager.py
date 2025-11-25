import os
import json
import threading
import bcrypt
from typing import Optional, Dict
from src.common.config import USER_DB_FILE, MAILBOXES_DIR
from src.common.logger import get_class_logger
from src.auth.user import User


class UserManager:
    """
    Singleton-like manager responsible for user lifecycle: loading, saving,
    creating, and authenticating users against the persistent store (users.json).
    """

    _instance = None
    _lock = threading.RLock()  # Re-entrant lock for thread safety across server threads

    def __new__(cls):
        # Ensure only one instance of UserManager exists in the application
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UserManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the manager and loads users from disk."""
        self.log = get_class_logger(self)
        # In-memory cache of User objects: {username_str: User_obj}
        self.users: Dict[str, User] = {}
        self.db_file = USER_DB_FILE
        self._load_users()
        self.log.info(f"UserManager initialized. Loaded {len(self.users)} users.")

    def _load_users(self):
        """Reads the users.json file and populates the in-memory cache."""
        with self._lock:
            if not os.path.exists(self.db_file):
                self.log.info("No user database found. Starting fresh.")
                # Create the database directory if it doesn't exist
                os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
                self._save_users()  # Initialize empty file
                return

            try:
                with open(self.db_file, "r") as f:
                    data = json.load(f)
                    for username, user_data in data.items():
                        self.users[username] = User.from_dict(user_data)
            except (json.JSONDecodeError, IOError) as e:
                self.log.error(f"Failed to load user database: {e}")

    def _save_users(self):
        """Persists current in-memory users to users.json using atomic write pattern."""
        with self._lock:
            try:
                # Convert cache back to dict of dicts for JSON
                data_to_save = {u.username: u.to_dict() for u in self.users.values()}

                # Atomic write pattern: write to temp file then rename
                tmp_file = f"{self.db_file}.tmp"
                with open(tmp_file, "w") as f:
                    json.dump(data_to_save, f, indent=2)
                os.replace(tmp_file, self.db_file)
                self.log.debug("User database saved successfully.")
            except IOError as e:
                self.log.error(f"Failed to save user database: {e}")

    def get_user(self, username: str) -> Optional[User]:
        """Retrieves a User object by username (case-insensitive)."""
        with self._lock:
            return self.users.get(username.lower())

    def create_user(self, username: str, password: str) -> User:
        """Creates a new user, hashes their password, saves to disk, and initializes mailbox."""
        with self._lock:
            lower_name = username.lower()
            if lower_name in self.users:
                raise ValueError(f"User '{username}' already exists.")

            new_user = User(lower_name)
            new_user.set_password(password)
            self.users[lower_name] = new_user

            # 1. Persist user credentials
            self._save_users()

            # 2. Initialize physical mailbox directory
            try:
                os.makedirs(new_user.mailbox_path, exist_ok=True)
                # Create initial empty metadata file for the Mailbox subsystem
                metadata_path = os.path.join(new_user.mailbox_path, "metadata.json")
                if not os.path.exists(metadata_path):
                    with open(metadata_path, "w") as f:
                        json.dump({"messages": []}, f)
            except OSError as e:
                self.log.error(
                    f"Failed to create mailbox directory for {username}: {e}"
                )
                # Note: In a production system, you might roll back user creation here.

            self.log.info(f"Created new user: {username}")
            return new_user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Attempts to authenticate a user. Returns User object on success, None on failure."""
        # No lock needed here, get_user handles read locking, verify_password doesn't modify state
        user = self.get_user(username)
        if user and user.verify_password(password):
            self.log.debug(f"Authentication successful for: {username}")
            return user
        self.log.warning(f"Authentication failed for: {username}")
        return None
