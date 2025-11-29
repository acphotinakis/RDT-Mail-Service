import argparse
import sys
import threading
import time

from src.common.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    POP3_SERVER_HOST,
    POP3_SERVER_PORT,
)
from src.smtp.smtp_server import SMTPServer
from src.pop3.pop3_server import POP3Server
from src.client.run_frontend import run_client_frontend

def main():
    """
    Main entry point for the email network service application.
    """
    parser = argparse.ArgumentParser(
        description="Run the SMTP/POP3 server or the email client."
    )
    parser.add_argument(
        "action",
        choices=["server", "client"],
        help="Whether to run the 'server' or the 'client'.",
    )
    args = parser.parse_args()

    if args.action == "server":
        run_server()
    elif args.action == "client":
        run_client()


def run_server():
    """
    Starts both the SMTP and POP3 servers in separate threads.
    """
    print("Starting email server...")

    # Initialize servers
    smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
    pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

    # Start servers in separate threads
    smtp_thread = threading.Thread(
        target=smtp_server.start, name="smtp-server", daemon=True
    )
    pop3_thread = threading.Thread(
        target=pop3_server.start, name="pop3-server", daemon=True
    )

    smtp_thread.start()
    pop3_thread.start()

    print(f"SMTP Server running on {SMTP_SERVER_HOST}:{SMTP_SERVER_PORT}")
    print(f"POP3 Server running on {POP3_SERVER_HOST}:{POP3_SERVER_PORT}")
    print("Servers are running. Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive to allow daemon threads to run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping servers...")
        smtp_server.stop()
        pop3_server.stop()
        print("Servers stopped.")
        sys.exit(0)


def run_client():
    """
    Starts the email client frontend.
    """
    print("Starting email client...")
    run_client_frontend()


if __name__ == "__main__":
    main()
