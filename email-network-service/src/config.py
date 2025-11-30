import os
import logging

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Network Configuration
# ------------------------------------------------------------------------------

# The IP address the servers (SMTP and POP3) will listen on.
# '127.0.0.1' (localhost) is standard for local testing.
# Use '0.0.0.0' to allow connections from other machines on the network.
SERVER_BIND_IP = "127.0.0.1"

# SMTP Server Configuration
SMTP_SERVER_HOST = SERVER_BIND_IP
SMTP_SERVER_PORT = 2525  # Use 2525 as 25 may require root

# POP3 Server Configuration
POP3_SERVER_HOST = SERVER_BIND_IP
POP3_SERVER_PORT = 1100  # Use 1100 as 110 may require root

# Client Configuration
CLIENT_IP = "127.0.0.1"
CLIENT_LISTENING_PORT = 2526

# ------------------------------------------------------------------------------
# RDT Protocol Configuration
# ------------------------------------------------------------------------------

RDT_TIMEOUT = 1.0  # Seconds to wait for ACK
RDT_RECV_BUFSIZE = 4096  # Max UDP packet size

# ------------------------------------------------------------------------------
# Storage / Database Configuration
# ------------------------------------------------------------------------------

BASE_DIR = os.getcwd()
DATABASE_PATH = os.path.join(BASE_DIR, "database")
USER_DB_FILE = os.path.join(DATABASE_PATH, "users.json")
MAILBOXES_DIR = os.path.join(DATABASE_PATH, "mailboxes")
TEMP_EMAILS_DIR = os.path.join(DATABASE_PATH, "temp")

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------

LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL


def log_config():
    """Logs the current configuration settings."""
    log.info("--- Application Configuration ---")
    # Network
    log.info(f"SERVER_BIND_IP: {SERVER_BIND_IP}")
    log.info(f"SMTP_SERVER_HOST: {SMTP_SERVER_HOST}")
    log.info(f"SMTP_SERVER_PORT: {SMTP_SERVER_PORT}")
    log.info(f"POP3_SERVER_HOST: {POP3_SERVER_HOST}")
    log.info(f"POP3_SERVER_PORT: {POP3_SERVER_PORT}")
    log.info(f"CLIENT_IP: {CLIENT_IP}")
    log.info(f"CLIENT_LISTENING_PORT: {CLIENT_LISTENING_PORT}")
    # RDT
    log.info(f"RDT_TIMEOUT: {RDT_TIMEOUT}")
    log.info(f"RDT_RECV_BUFSIZE: {RDT_RECV_BUFSIZE}")
    # Storage
    log.info(f"DATABASE_PATH: {DATABASE_PATH}")
    log.info(f"USER_DB_FILE: {USER_DB_FILE}")
    log.info(f"MAILBOXES_DIR: {MAILBOXES_DIR}")
    log.info(f"TEMP_EMAILS_DIR: {TEMP_EMAILS_DIR}")
    # Logging
    log.info(f"LOG_LEVEL: {LOG_LEVEL}")
    log.info("-----------------------------")
