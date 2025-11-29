import random
import time
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.auth.user_manager import UserManager
from src.smtp.smtp_client import SMTPClient
from src.common.logger import setup_logger, get_class_logger


class Simulation:
    """
    Simulates user creation and email sending.
    """

    def __init__(self, num_users: int = 5):
        """
        Initializes the simulation environment.
        Args:
            num_users: The number of users to simulate.
        """
        self.log = get_class_logger(self)
        self.num_users = num_users
        self.users = []
        self.user_manager = UserManager()

    def setup_users(self):
        """
        Creates simulation users if they don't already exist.
        """
        self.log.info(f"Setting up {self.num_users} simulation users...")
        for i in range(1, self.num_users + 1):
            username = f"user{i}"
            password = "password"  # Using a simple password for simulation purposes
            user = self.user_manager.get_user(username)
            if not user:
                self.log.info(f"User '{username}' not found, creating...")
                user = self.user_manager.create_user(username, password)
            else:
                self.log.info(f"User '{username}' already exists.")
            self.users.append(user)
        self.log.info("User setup complete.")

    def run_email_simulation(self):
        """
        Simulates each user sending an email to another random user.
        """
        self.log.info("Starting email sending simulation...")
        if not self.users:
            self.log.error("No users configured for simulation. Run setup_users first.")
            return

        for sender_user in self.users:
            # Ensure the recipient is not the sender
            possible_recipients = [u for u in self.users if u.username != sender_user.username]
            if not possible_recipients:
                self.log.warning(f"User {sender_user.username} has no one to send an email to.")
                continue

            recipient_user = random.choice(possible_recipients)

            sender_email = f"{sender_user.username}@localhost"
            recipient_email = f"{recipient_user.username}@localhost"

            subject = f"Simulation email from {sender_user.username}"
            body = (
                f"Hello {recipient_user.username},\n\n"
                f"This is a test email sent at {time.ctime()}\n\n"
                f"From,\n{sender_user.username}"
            )

            self.log.info(f"Preparing to send email from {sender_email} to {recipient_email}")

            smtp_client = SMTPClient()
            success = smtp_client.send_email(
                sender=sender_email,
                recipient=recipient_email,
                subject=subject,
                body=body,
            )

            if success:
                self.log.info(f"Successfully sent email from {sender_email} to {recipient_email}")
            else:
                self.log.error(f"Failed to send email from {sender_email} to {recipient_email}")

            # A small delay to make the simulation observable and avoid overwhelming the server
            time.sleep(1)

        self.log.info("Email sending simulation finished.")


def main():
    """
    Main function to run the simulation.
    """
    # Note: Ensure that the SMTP server is running before starting the simulation.
    # You can run the server using: python src/main.py server
    setup_logger("SIMULATION", level="INFO")
    simulation = Simulation(num_users=5)
    simulation.setup_users()
    simulation.run_email_simulation()


if __name__ == "__main__":
    main()
