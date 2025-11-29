# src/common/config.py additions:
import os

# The root of the runtime database directory
DATABASE_PATH = os.path.join(os.getcwd(), "database")

# The specific file holding user credentials
USER_DB_FILE = os.path.join(DATABASE_PATH, "users.json")

# The directory holding user mailboxes
MAILBOXES_DIR = os.path.join(DATABASE_PATH, "mailboxes")

# The directory holding temp emails
TEMP_EMAILS_DIR = os.path.join(DATABASE_PATH, "temp_emails")


import os

# ------------------------------------------------------------------------------
# Network Configuration
# ------------------------------------------------------------------------------

# The IP address the servers (SMTP and POP3) will listen on.
# '127.0.0.1' (localhost) is standard for local testing.
# Use '0.0.0.0' to allow connections from other machines on the network.
SERVER_BIND_IP = "127.0.0.1"

# SMTP Server Configuration
SMTP_SERVER_HOST = SERVER_BIND_IP
# We use 2525 because standard port 25 often requires root privileges
SMTP_SERVER_PORT = 2525

# POP3 Server Configuration
POP3_SERVER_HOST = SERVER_BIND_IP
# We use 1100 because standard port 110 often requires root privileges
POP3_SERVER_PORT = 1100

# Client Configuration
CLIENT_IP = "127.0.0.1"
# The specific port the client's RDTReceiver binds to for listening to server responses.
# In a full production system, this might be dynamic (ephemeral), but fixed helps RDT logic here.
CLIENT_LISTENING_PORT = 2526


# ------------------------------------------------------------------------------
# RDT Protocol Configuration
# ------------------------------------------------------------------------------

# Time (in seconds) to wait for an ACK before retransmitting a packet
RDT_TIMEOUT = 2.0

# Maximum size (in bytes) of a UDP packet payload to accept
# This must be large enough to hold your largest expected JSON header + data chunk
RDT_RECV_BUFSIZE = 4096


# ------------------------------------------------------------------------------
# Storage / Database Configuration
# ------------------------------------------------------------------------------

# Root directory for runtime data
BASE_DIR = os.getcwd()
DATABASE_PATH = os.path.join(BASE_DIR, "database")

# Path to the JSON file storing user credentials
USER_DB_FILE = os.path.join(DATABASE_PATH, "users.json")

# Directory where user mailboxes (and their metadata.json files) are stored
MAILBOXES_DIR = os.path.join(DATABASE_PATH, "mailboxes")

# Directory for temporary files during atomic write operations
TEMP_EMAILS_DIR = os.path.join(DATABASE_PATH, "temp")


# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
