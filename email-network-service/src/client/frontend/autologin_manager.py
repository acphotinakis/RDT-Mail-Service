import json
import os
from typing import Optional, Tuple

# Simple config file to store autologin credentials.
# In a real app, this would be in a more standard user config location.
AUTOLOGIN_FILE = ".autologin.json"


def get_saved_credentials() -> Optional[Tuple[str, str]]:
    """
    Reads saved credentials from the autologin file.
    Returns (username, password) or None if not found or invalid.
    """
    if not os.path.exists(AUTOLOGIN_FILE):
        return None

    try:
        with open(AUTOLOGIN_FILE, "r") as f:
            data = json.load(f)
            username = data.get("username")
            password = data.get("password")
            if username and password:
                return username, password
    except (json.JSONDecodeError, IOError):
        # If file is corrupted or unreadable, treat as if it doesn't exist.
        return None
    
    return None


def save_credentials(username: str, password: str):
    """
    Saves credentials to the autologin file.
    WARNING: This stores the password in plain text.
    """
    try:
        with open(AUTOLOGIN_FILE, "w") as f:
            json.dump({"username": username, "password": password}, f, indent=2)
        # Restrict permissions to only the current user
        os.chmod(AUTOLOGIN_FILE, 0o600)
    except IOError:
        # Failed to write file, can't do much.
        pass


def delete_credentials():
    """Deletes the autologin file if it exists."""
    if os.path.exists(AUTOLOGIN_FILE):
        try:
            os.remove(AUTOLOGIN_FILE)
        except OSError:
            pass
