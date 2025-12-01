import argparse
import sys
import threading
import time


from src.config import Config
from src.common.logger import setup_logger, get_class_logger
from src.smtp.smtp_server import SMTPServer
from src.pop3.pop3_server import POP3Server
from src.client.run_frontend import run_frontend


class Main:
    def __init__(self):
        setup_logger("MAIN", level=Config.LOG_LEVEL)
        self.log = get_class_logger(self)

    def main(self):
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
            self.log.info("Running in SERVER mode.")
            self.run_server()
        elif args.action == "client":
            self.log.info("Running in CLIENT mode.")
            self.run_client()

    def run_server(self):
        """
        Starts both the SMTP and POP3 servers in separate threads.
        """
        self.log.info("Starting email server...")

        # Initialize servers
        smtp_server = SMTPServer(Config.SMTP_SERVER_HOST, Config.SMTP_SERVER_PORT)
        pop3_server = POP3Server(Config.POP3_SERVER_HOST, Config.POP3_SERVER_PORT)

        # Start servers in separate threads
        smtp_thread = threading.Thread(target=smtp_server.start, name="smtp-server", daemon=True)
        pop3_thread = threading.Thread(target=pop3_server.start, name="pop3-server", daemon=True)

        smtp_thread.start()
        pop3_thread.start()

        self.log.info(f"SMTP Server running on {Config.SMTP_SERVER_HOST}:{Config.SMTP_SERVER_PORT}")
        self.log.info(f"POP3 Server running on {Config.POP3_SERVER_HOST}:{Config.POP3_SERVER_PORT}")
        print("Servers are running. Press Ctrl+C to stop.")

        try:
            # Keep the main thread alive to allow daemon threads to run
            while smtp_thread.is_alive() and pop3_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            self.log.info("Keyboard interrupt received. Stopping servers...")
            smtp_server.stop()
            pop3_server.stop()
            self.log.info("Servers stopped.")
            sys.exit(0)

    def run_client(self):
        """
        Starts the email client frontend.
        """
        self.log.info("Starting email client...")
        run_frontend()
        self.log.info("Email client stopped.")


if __name__ == "__main__":
    runner = Main()
    runner.main()
