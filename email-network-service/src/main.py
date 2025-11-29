import argparse
import sys
import threading
import time
import logging

from src.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    POP3_SERVER_HOST,
    POP3_SERVER_PORT,
    LOG_LEVEL,
    log_config,
)
from src.common.logger import setup_logger
from src.smtp.smtp_server import SMTPServer
from src.pop3.pop3_server import POP3Server
from src.client.run_frontend import run_frontend

log = logging.getLogger(__name__)


def main():
    """
    Main entry point for the email network service application.
    """
    setup_logger("MAIN", level=LOG_LEVEL)
    log_config()

    parser = argparse.ArgumentParser(description="Run the SMTP/POP3 server or the email client.")
    parser.add_argument(
        "action",
        choices=["server", "client"],
        help="Whether to run the 'server' or the 'client'.",
    )
    args = parser.parse_args()

    if args.action == "server":
        log.info("Running in SERVER mode.")
        run_server()
    elif args.action == "client":
        log.info("Running in CLIENT mode.")
        run_client()


def run_server():
    """
    Starts both the SMTP and POP3 servers in separate threads.
    """
    log.info("Starting email server...")

    # Initialize servers
    smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
    pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

    # Start servers in separate threads
    smtp_thread = threading.Thread(target=smtp_server.start, name="smtp-server", daemon=True)
    pop3_thread = threading.Thread(target=pop3_server.start, name="pop3-server", daemon=True)

    smtp_thread.start()
    pop3_thread.start()

    log.info(f"SMTP Server running on {SMTP_SERVER_HOST}:{SMTP_SERVER_PORT}")
    log.info(f"POP3 Server running on {POP3_SERVER_HOST}:{POP3_SERVER_PORT}")
    print("Servers are running. Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive to allow daemon threads to run
        while smtp_thread.is_alive() and pop3_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received. Stopping servers...")
        smtp_server.stop()
        pop3_server.stop()
        log.info("Servers stopped.")
        sys.exit(0)


def run_client():
    """
    Starts the email client frontend.
    """
    log.info("Starting email client...")
    run_frontend()
    log.info("Email client stopped.")


if __name__ == "__main__":
    main()
