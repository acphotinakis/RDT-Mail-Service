# src/common/config.py additions:
import os

# The root of the runtime database directory
DATABASE_PATH = os.path.join(os.getcwd(), "database")

# The specific file holding user credentials
USER_DB_FILE = os.path.join(DATABASE_PATH, "users.json")

# The directory holding user mailboxes
MAILBOXES_DIR = os.path.join(DATABASE_PATH, "mailboxes")
