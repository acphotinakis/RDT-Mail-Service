import os
import json
import threading
import bcrypt
from typing import Optional, Dict
from src.config import Config.USER_DB_FILE, Config.MAILBOXES_DIR
from src.common.logger import get_class_logger
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
                    cls.log = get_class_logger(cls)
                    cls.log.debug("Creating new UserManager instance")
                    cls._instance = super(UserManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the manager and loads users from disk."""
        self.log = get_class_logger(self)
        # In-memory cache of User objects: {username_str: User_obj}
        self.users: Dict[str, User] = {}
        self.db_file = Config.USER_DB_FILE
        self._load_users()
        self.log.info(f"UserManager initialized. Loaded {len(self.users)} users.")

    def _load_users(self):
        """Reads the users.json file and populates the in-memory cache."""
        with self._lock:
            if not os.path.exists(self.db_file):
                self.log.info("No user database found. Starting fresh.")
                os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
                self.log.debug(f"Created directory {os.path.dirname(self.db_file)}")
                self._save_users()  # Initialize empty file
                return

            try:
                self.log.debug(f"Loading users from {self.db_file}")
                with open(self.db_file, "r") as f:
                    data = json.load(f)
                    users_list = data.get("users", [])
                    if not isinstance(users_list, list):
                        raise ValueError("Invalid users.json format (users is not a list)")
                    for user_data in users_list:
                        try:
                            user = User.from_dict(user_data)
                            self.users[user.username] = user
                            self.log.debug(f"Loaded user: {user.username}")
                        except ValueError as e:
                            self.log.warning(f"Skipping invalid user record: {e}")
            except (json.JSONDecodeError, IOError, ValueError) as e:
                self.log.error(f"Failed to load user database: {e}")

    def _save_users(self):
        """Persists current users to users.json using list format."""
        with self._lock:
            try:
                self.log.debug("Saving user database.")

                # Convert user cache → list
                users_list = [u.to_dict() for u in self.users.values()]

                tmp_file = f"{self.db_file}.tmp"
                with open(tmp_file, "w") as f:
                    json.dump({"users": users_list}, f, indent=2)

                os.replace(tmp_file, self.db_file)
                self.log.debug("User database saved successfully.")
            except IOError as e:
                self.log.error(f"Failed to save user database: {e}")

    def get_user(self, username: str) -> Optional[User]:
        """Retrieves a User object by username (case-insensitive)."""
        with self._lock:
            self.log.debug(f"Attempting to get user: {username}")
            user = self.users.get(username.lower())
            if user:
                self.log.debug(f"User found: {username}")
            else:
                self.log.debug(f"User not found: {username}")
            return user

    def create_user(self, username: str, password: str) -> User:
        """Creates a new user, hashes their password, saves to disk, and initializes mailbox."""
        with self._lock:
            lower_name = username.lower()
            if lower_name in self.users:
                self.log.warning(f"Attempted to create existing user: {username}")
                raise ValueError(f"User '{username}' already exists.")

            self.log.debug(f"Creating new user: {username}")
            new_user = User(lower_name, password)
            self.users[lower_name] = new_user

            # 1. Persist user credentials
            self._save_users()

            # 2. Initialize physical mailbox directory
            try:
                self.log.debug(
                    f"Creating mailbox directory for {username} at {new_user.mailbox_path}"
                )
                os.makedirs(new_user.mailbox_path, exist_ok=True)
                # Create initial empty metadata file for the Mailbox subsystem
                metadata_path = os.path.join(new_user.mailbox_path, "metadata.json")
                if not os.path.exists(metadata_path):
                    self.log.debug(f"Creating metadata file for {username} at {metadata_path}")
                    with open(metadata_path, "w") as f:
                        json.dump({"messages": {}}, f)
            except OSError as e:
                self.log.error(f"Failed to create mailbox directory for {username}: {e}")
                # Note: In a production system, you might roll back user creation here.

            self.log.info(f"Created new user: {username}")
            return new_user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Attempts to authenticate a user. Returns User object on success, None on failure."""
        self.log.debug(f"Attempting to authenticate user: {username}")
        # No lock needed here, get_user handles read locking, verify_password doesn't modify state
        user = self.get_user(username)
        if user and user.verify_password(password):
            self.log.debug(f"Authentication successful for: {username}")
            return user
        self.log.warning(f"Authentication failed for: {username}")
        return None
