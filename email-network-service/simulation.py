import random
import time
import sys
import os
import threading

# --- Path Setup ---
# Ensure we can import 'src' regardless of where this script is run
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "src")):
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.dirname(current_dir))

from src.auth.user_manager import UserManager
from src.smtp.smtp_client import SMTPClient
from src.smtp.smtp_server import SMTPServer
from src.pop3.pop3_server import POP3Server
from src.config import SMTP_SERVER_HOST, SMTP_SERVER_PORT, POP3_SERVER_HOST, POP3_SERVER_PORT
from src.common.logger import setup_logger, get_class_logger


class Simulation:
    """
    Simulates user creation and email sending.
    Automatically spins up local SMTP/POP3 servers for the duration of the test.
    """

    def __init__(self, num_users: int = 5):
        self.log = get_class_logger(self)
        self.num_users = num_users
        self.users = []
        self.user_manager = UserManager()

        # Server instances
        self.smtp_server = None
        self.pop3_server = None

    def start_servers(self):
        """Starts the SMTP and POP3 servers in background threads."""
        self.log.info("--- 🚀 STARTING INFRASTRUCTURE ---")

        # Initialize Servers
        self.smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
        self.pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

        # Start them
        self.smtp_server.start()
        self.pop3_server.start()

        # Give them a moment to bind sockets
        time.sleep(0.5)
        self.log.info("Servers are running in background threads.")

    def stop_servers(self):
        """Stops the background servers."""
        self.log.info("--- 🛑 SHUTTING DOWN INFRASTRUCTURE ---")
        if self.smtp_server:
            self.smtp_server.stop()
        if self.pop3_server:
            self.pop3_server.stop()

    def setup_users(self):
        self.log.info(f"Setting up {self.num_users} simulation users...")
        for i in range(1, self.num_users + 1):
            username = f"user{i}"
            password = "password"

            user = self.user_manager.get_user(username)
            if not user:
                user = self.user_manager.create_user(username, password)

            self.users.append(user)
        self.log.info(f"User setup complete: {[u.username for u in self.users]}")

    def run_email_simulation(self):
        self.log.info("--- 📨 STARTING EMAIL TRAFFIC ---")

        if len(self.users) < 2:
            self.log.error("Need at least 2 users to run simulation.")
            return

        for i, sender_user in enumerate(self.users):
            # Pick a random recipient
            possible_recipients = [u for u in self.users if u.username != sender_user.username]
            recipient_user = random.choice(possible_recipients)

            sender_email = f"{sender_user.username}@localhost"
            recipient_email = f"{recipient_user.username}@localhost"

            subject = f"Hello from {sender_user.username}"
            body = (
                f"Hi {recipient_user.username},\n\n"
                f"This is simulation message #{i+1} sent via RDT 3.0!\n"
                f"Timestamp: {time.ctime()}\n\n"
                f"Regards,\n{sender_user.username}"
            )

            self.log.info(f"Attempting: {sender_user.username} -> {recipient_user.username}")

            # Retry loop for client socket binding
            smtp_client = None
            for attempt in range(3):
                try:
                    smtp_client = SMTPClient()
                    break
                except OSError:
                    time.sleep(0.5)

            if not smtp_client:
                self.log.error("Could not bind client socket. Skipping.")
                continue

            success = smtp_client.send_email(
                sender=sender_email,
                recipient=recipient_email,
                subject=subject,
                body=body,
            )

            if success:
                self.log.info("✅ Delivery Confirmed.")
            else:
                self.log.error("❌ Delivery Failed.")

            time.sleep(0.5)


def main():
    setup_logger("SIM", level="INFO")

    # Ensure storage exists
    if not os.path.exists("mailboxes"):
        os.makedirs("mailboxes")

    sim = Simulation(num_users=3)

    try:
        # 1. Start Servers (The missing step from before)
        sim.start_servers()

        # 2. Run Logic
        sim.setup_users()
        sim.run_email_simulation()

    except KeyboardInterrupt:
        print("\nSimulation aborted.")
    finally:
        # 3. Cleanup
        sim.stop_servers()


if __name__ == "__main__":
    main()


# import random
# import time
# import sys
# import os

# # Add the project root to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from src.auth.user_manager import UserManager
# from src.smtp.smtp_client import SMTPClient
# from src.common.logger import setup_logger, get_class_logger


# class Simulation:
#     """
#     Simulates user creation and email sending.
#     """

#     def __init__(self, num_users: int = 5):
#         """
#         Initializes the simulation environment.
#         Args:
#             num_users: The number of users to simulate.
#         """
#         self.log = get_class_logger(self)
#         self.num_users = num_users
#         self.users = []
#         self.user_manager = UserManager()

#     def setup_users(self):
#         """
#         Creates simulation users if they don't already exist.
#         """
#         self.log.info(f"Setting up {self.num_users} simulation users...")
#         for i in range(1, self.num_users + 1):
#             username = f"user{i}"
#             password = "password"  # Using a simple password for simulation purposes
#             user = self.user_manager.get_user(username)
#             if not user:
#                 self.log.info(f"User '{username}' not found, creating...")
#                 user = self.user_manager.create_user(username, password)
#             else:
#                 self.log.info(f"User '{username}' already exists.")
#             self.users.append(user)
#         self.log.info("User setup complete.")

#     def run_email_simulation(self):
#         """
#         Simulates each user sending an email to another random user.
#         """
#         self.log.info("Starting email sending simulation...")
#         if not self.users:
#             self.log.error("No users configured for simulation. Run setup_users first.")
#             return

#         for sender_user in self.users:
#             # Ensure the recipient is not the sender
#             possible_recipients = [u for u in self.users if u.username != sender_user.username]
#             if not possible_recipients:
#                 self.log.warning(f"User {sender_user.username} has no one to send an email to.")
#                 continue

#             recipient_user = random.choice(possible_recipients)

#             sender_email = f"{sender_user.username}@localhost"
#             recipient_email = f"{recipient_user.username}@localhost"

#             subject = f"Simulation email from {sender_user.username}"
#             body = (
#                 f"Hello {recipient_user.username},\n\n"
#                 f"This is a test email sent at {time.ctime()}\n\n"
#                 f"From,\n{sender_user.username}"
#             )

#             self.log.info(f"Preparing to send email from {sender_email} to {recipient_email}")

#             smtp_client = SMTPClient()
#             success = smtp_client.send_email(
#                 sender=sender_email,
#                 recipient=recipient_email,
#                 subject=subject,
#                 body=body,
#             )

#             if success:
#                 self.log.info(f"Successfully sent email from {sender_email} to {recipient_email}")
#             else:
#                 self.log.error(f"Failed to send email from {sender_email} to {recipient_email}")

#             # A small delay to make the simulation observable and avoid overwhelming the server
#             time.sleep(1)

#         self.log.info("Email sending simulation finished.")


# def main():
#     """
#     Main function to run the simulation.
#     """
#     # Note: Ensure that the SMTP server is running before starting the simulation.
#     # You can run the server using: python src/main.py server
#     setup_logger("SIMULATION", level="INFO")
#     simulation = Simulation(num_users=5)
#     simulation.setup_users()
#     simulation.run_email_simulation()


# if __name__ == "__main__":
#     main()
