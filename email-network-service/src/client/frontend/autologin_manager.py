import json
import os
from typing import Optional, Tuple
from src.config import Config

from src.common.logger import get_class_logger

log = get_class_logger("STORAGE_WRAPPER_QT")


def get_saved_credentials() -> Optional[Tuple[str, str]]:
    """
    Reads saved credentials from the autologin file.
    Returns (username, password) or None if not found or invalid.
    """
    if not os.path.exists(Config.AUTOLOGIN_FILE):
        log.info("No autologin file found.")
        return None

    try:
        with open(Config.AUTOLOGIN_FILE, "r") as f:
            data = json.load(f)
            username = data.get("username")
            password = data.get("password")
            if username and password:
                log.info(f"Found saved credentials for user: {username}")
                return username, password
            log.warning("Autologin file is missing username or password.")
            return None
    except (json.JSONDecodeError, IOError) as e:
        # If file is corrupted or unreadable, treat as if it doesn't exist.
        log.error(f"Failed to read autologin file: {e}")
        return None


def save_credentials(username: str, password: str):
    """
    Saves credentials to the autologin file.
    WARNING: This stores the password in plain text.
    """
    try:
        with open(Config.AUTOLOGIN_FILE, "w") as f:
            json.dump({"username": username, "password": password}, f, indent=2)
        # Restrict permissions to only the current user
        os.chmod(Config.AUTOLOGIN_FILE, 0o600)
        log.info(f"Saved credentials for user: {username}")
    except IOError as e:
        # Failed to write file, can't do much.
        log.error(f"Failed to save autologin file: {e}")
        pass


def delete_credentials():
    """Deletes the autologin file if it exists."""
    if os.path.exists(Config.AUTOLOGIN_FILE):
        try:
            os.remove(Config.AUTOLOGIN_FILE)
            log.info("Deleted autologin file.")
        except OSError as e:
            log.error(f"Failed to delete autologin file: {e}")
            pass
