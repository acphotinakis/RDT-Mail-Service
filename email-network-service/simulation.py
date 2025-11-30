"""
===============================================================
         ADVANCED NETWORKED EMAIL SYSTEM SIMULATION
===============================================================
"""

import random
import time
import sys
import os
import threading
import traceback

# ----------------------------------------------
#  Import Setup
# ----------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "src")):
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.dirname(current_dir))

from src.auth.user_manager import UserManager
from src.smtp.smtp_client import SMTPClient
from src.smtp.smtp_server import SMTPServer
from src.pop3.pop3_server import POP3Server
from src.pop3.pop3_client import POP3Client
from src.config import (
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    POP3_SERVER_HOST,
    POP3_SERVER_PORT,
)
from src.common.logger import setup_logger, get_class_logger


class Simulation:
    def __init__(self, num_users: int = 5, concurrency: int = 5):
        self.log = get_class_logger(self)
        self.num_users = num_users
        self.concurrency = concurrency
        self.users = []
        self.user_manager = UserManager()

        # Servers
        self.smtp_server = None
        self.pop3_server = None

        # For POP3 integrity verification
        self.sent_messages = []  # List[ (sender, recipient, subject, body) ]

    # ----------------------------------------------
    # Infrastructure Management
    # ----------------------------------------------
    def start_servers(self):
        self.log.info("=== 🚀 PHASE 1: STARTING INFRASTRUCTURE ===")

        self.smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
        self.pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

        self.smtp_server.start()
        self.pop3_server.start()

        # Allow sockets to bind
        time.sleep(1.0)
        self.log.info("SMTP + POP3 servers running.")

    def stop_servers(self):
        self.log.info("=== 🛑 SHUTDOWN INFRASTRUCTURE ===")
        if self.smtp_server:
            self.smtp_server.stop()
        if self.pop3_server:
            self.pop3_server.stop()

    # ----------------------------------------------
    # User Setup
    # ----------------------------------------------
    def setup_users(self):
        self.log.info(f"=== 👤 PHASE 2: Creating {self.num_users} Users ===")
        for i in range(1, self.num_users + 1):
            username = f"user{i}"
            password = "password"

            user = self.user_manager.get_user(username)
            if not user:
                user = self.user_manager.create_user(username, password)

            self.users.append(user)
        self.log.info("Users ready: " + ", ".join(u.username for u in self.users))

    # ================================================================
    #           CORE: MULTI-THREADED EMAIL SENDING
    # ================================================================
    def _smtp_send_task(self, sender_user):
        try:
            # Choose a recipient
            recipient_user = random.choice(
                [u for u in self.users if u.username != sender_user.username]
            )

            sender_email = f"{sender_user.username}@localhost"
            recipient_email = f"{recipient_user.username}@localhost"

            subject = f"[Sim] From {sender_user.username} {random.randint(1000,9999)}"
            body = (
                f"Hello {recipient_user.username},\n"
                f"This is a concurrency test message.\n"
                f"Timestamp: {time.time()}\n"
            )

            # Record for POP3 verification
            self.sent_messages.append((sender_email, recipient_email, subject, body))

            self.log.info(f"[SMTP] {sender_user.username} -> {recipient_user.username}")

            # Note: SMTPClient must use ephemeral ports (bind to 0) for this to work concurrently
            smtp_client = SMTPClient()
            ok = smtp_client.send_email(
                sender=sender_email,
                recipient=recipient_email,
                subject=subject,
                body=body,
            )

            if ok:
                self.log.info(f"[SMTP] Delivery OK ({sender_user.username})")
            else:
                self.log.error(f"[SMTP] Delivery FAILED ({sender_user.username})")

        except Exception as e:
            self.log.error(f"[SMTP THREAD ERROR]: {e}")
            traceback.print_exc()

    # ================================================================
    #           POP3 CONSISTENCY VERIFICATION
    # ================================================================
    def run_pop3_integrity_check(self):
        """
        Ensures messages that were sent exist in mailbox via POP3.
        """
        self.log.info("=== 📥 PHASE 4: POP3 Consistency Verification ===")

        def extract_subject(raw_text):
            for line in raw_text.splitlines():
                if line.lower().startswith("subject:"):
                    return line[8:].strip()
            return ""

        for user in self.users:
            self.log.info(f"[POP3] Checking mailbox of {user.username}")

            client = POP3Client()
            # FIX: Pass credentials to the helper method
            raw_messages = client.get_all_messages(user.username, "password")

            # Parse subjects from raw email strings
            received_subjects = {extract_subject(msg) for msg in raw_messages}

            # Look for matching subjects
            for sender, recipient, subject, _ in self.sent_messages:
                if recipient.startswith(user.username):
                    if subject in received_subjects:
                        self.log.info(f"  ✅ Verified: {subject}")
                    else:
                        self.log.error(
                            f"  ❌ MISSING: {subject} (Expected in {user.username}'s inbox)"
                        )

        self.log.info("POP3 verification completed.")

    def run_email_simulation(self):
        self.log.info("=== 📨 PHASE 3: Multi-Threaded Email Traffic ===")

        threads = []
        for user in self.users:
            t = threading.Thread(target=self._smtp_send_task, args=(user,), daemon=True)
            t.start()
            threads.append(t)
            time.sleep(random.uniform(0.1, 0.3))

        for t in threads:
            t.join()

        self.log.info("SMTP concurrency simulation finished.")

    def run(self):
        self.start_servers()
        self.setup_users()
        self.run_email_simulation()
        # Wait a moment for server to flush to disk
        time.sleep(1.0)
        self.run_pop3_integrity_check()
        self.stop_servers()


def main():
    setup_logger("SIM", level="INFO")

    if not os.path.exists("mailboxes"):
        os.makedirs("mailboxes")

    sim = Simulation(num_users=5, concurrency=5)

    try:
        sim.run()
    except KeyboardInterrupt:
        print("Simulation interrupted.")
    finally:
        sim.stop_servers()


if __name__ == "__main__":
    main()


# """
# ===============================================================
#          ADVANCED NETWORKED EMAIL SYSTEM SIMULATION
# ===============================================================

# This script performs a deep, concurrency-focused simulation of:

#     - SMTP Client/Server (custom, state-machine based)
#     - POP3  Client/Server (custom, state-machine based)
#     - RDT 3.0 (stop-and-wait) transport layer over UDP
#     - Mailbox creation, reading, consistency verification

# It models:
#     • Multiple users
#     • Concurrent SMTP clients
#     • Randomized delivery patterns
#     • RDT retransmission pressure
#     • POP3 stress reading after SMTP load
#     • Integrity verification that POP3 content matches SMTP sent content
#     • Protocol-level logging and timing analysis

# This framework is designed for:
#     - Stress-testing your RDT implementation
#     - Surfacing race conditions
#     - Verifying correctness under concurrency
#     - Load generation
#     - Academic project demos & debugging

# ===============================================================
# """

# import random
# import time
# import sys
# import os
# import threading
# import traceback

# # ----------------------------------------------
# #  Import Setup
# # ----------------------------------------------
# current_dir = os.path.dirname(os.path.abspath(__file__))
# if os.path.exists(os.path.join(current_dir, "src")):
#     sys.path.append(current_dir)
# else:
#     sys.path.append(os.path.dirname(current_dir))

# from src.auth.user_manager import UserManager
# from src.smtp.smtp_client import SMTPClient
# from src.smtp.smtp_server import SMTPServer
# from src.pop3.pop3_server import POP3Server
# from src.pop3.pop3_client import POP3Client
# from src.config import (
#     SMTP_SERVER_HOST,
#     SMTP_SERVER_PORT,
#     POP3_SERVER_HOST,
#     POP3_SERVER_PORT,
# )
# from src.common.logger import setup_logger, get_class_logger


# # ================================================================
# #                 ADVANCED SIMULATION CLASS
# # ================================================================
# class Simulation:
#     """
#     Network-level simulation with concurrency and integrity testing.

#     PHASES:
#         1. Infrastructure Boot: start SMTP/POP3 servers
#         2. User Setup
#         3. SMTP Multi-Threaded Message Dispatch
#         4. POP3 Retrieval Consistency Verification
#         5. Optional Stress Conditions:
#               - Random socket churn
#               - Artificial lag
#               - Burst message storms
#     """

#     def __init__(self, num_users: int = 5, concurrency: int = 5):
#         self.log = get_class_logger(self)
#         self.num_users = num_users
#         self.concurrency = concurrency
#         self.users = []
#         self.user_manager = UserManager()

#         # Servers
#         self.smtp_server = None
#         self.pop3_server = None

#         # For POP3 integrity verification
#         self.sent_messages = []  # List[ (sender, recipient, subject, body) ]

#     # ----------------------------------------------
#     # Infrastructure Management
#     # ----------------------------------------------
#     def start_servers(self):
#         self.log.info("=== 🚀 PHASE 1: STARTING INFRASTRUCTURE ===")

#         self.smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
#         self.pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

#         self.smtp_server.start()
#         self.pop3_server.start()

#         # Allow sockets to bind
#         time.sleep(1.0)

#         self.log.info("SMTP + POP3 servers running.")

#     def stop_servers(self):
#         self.log.info("=== 🛑 SHUTDOWN INFRASTRUCTURE ===")
#         if self.smtp_server:
#             self.smtp_server.stop()
#         if self.pop3_server:
#             self.pop3_server.stop()

#     # ----------------------------------------------
#     # User Setup
#     # ----------------------------------------------
#     def setup_users(self):
#         self.log.info(f"=== 👤 PHASE 2: Creating {self.num_users} Users ===")
#         for i in range(1, self.num_users + 1):
#             username = f"user{i}"
#             password = "password"

#             user = self.user_manager.get_user(username)
#             if not user:
#                 user = self.user_manager.create_user(username, password)

#             self.users.append(user)

#         self.log.info("Users ready: " + ", ".join(u.username for u in self.users))

#     # ================================================================
#     #           CORE: MULTI-THREADED EMAIL SENDING
#     # ================================================================
#     def _smtp_send_task(self, sender_user):
#         """
#         SMTP workload for one client.
#         """
#         try:
#             # Choose a recipient
#             recipient_user = random.choice(
#                 [u for u in self.users if u.username != sender_user.username]
#             )

#             sender_email = f"{sender_user.username}@localhost"
#             recipient_email = f"{recipient_user.username}@localhost"

#             subject = f"[Sim] From {sender_user.username}"
#             body = (
#                 f"Hello {recipient_user.username},\n"
#                 f"This is a concurrency test message.\n"
#                 f"Timestamp: {time.time()}\n"
#             )

#             # Record for POP3 verification
#             self.sent_messages.append((sender_email, recipient_email, subject, body))

#             self.log.info(f"[SMTP] {sender_user.username} -> {recipient_user.username}")

#             smtp_client = SMTPClient()
#             ok = smtp_client.send_email(
#                 sender=sender_email,
#                 recipient=recipient_email,
#                 subject=subject,
#                 body=body,
#             )

#             if ok:
#                 self.log.info(f"[SMTP] Delivery OK ({sender_user.username})")
#             else:
#                 self.log.error(f"[SMTP] Delivery FAILED ({sender_user.username})")

#         except Exception as e:
#             self.log.error(f"[SMTP THREAD ERROR]: {e}")
#             traceback.print_exc()

#     # ================================================================
#     #           POP3 CONSISTENCY VERIFICATION
#     # ================================================================
#     def run_pop3_integrity_check(self):
#         """
#         Ensures messages that were sent exist in mailbox via POP3.
#         """
#         self.log.info("=== 📥 PHASE 4: POP3 Consistency Verification ===")

#         for user in self.users:
#             self.log.info(f"[POP3] Checking mailbox of {user.username}")

#             client = POP3Client()
#             messages = client.get_all_messages()

#             subjects = {msg.subject for msg in messages}

#             # Look for matching subjects
#             for _, recipient, subject, _ in self.sent_messages:
#                 if recipient.startswith(user.username):
#                     if subject not in subjects:
#                         self.log.error(f"[POP3] MISSING message for {user.username}: {subject}")

#         self.log.info("POP3 verification completed.")

#     # ================================================================
#     #           MAIN SMTP CONCURRENCY SIMULATION
#     # ================================================================
#     def run_email_simulation(self):
#         self.log.info("=== 📨 PHASE 3: Multi-Threaded Email Traffic ===")

#         threads = []
#         for user in self.users:
#             t = threading.Thread(target=self._smtp_send_task, args=(user,), daemon=True)
#             t.start()
#             threads.append(t)

#             # Optional:
#             time.sleep(random.uniform(0.1, 0.3))

#         for t in threads:
#             t.join()

#         self.log.info("SMTP concurrency simulation finished.")

#     # ================================================================
#     #   OPTIONAL: CHAOS MODE (simulate stress, failures, delays)
#     # ================================================================
#     def chaos_mode(self):
#         """
#         Simulate real-world network jitter, packet loss, and random restarts.
#         """
#         self.log.warning("=== ⚡ CHAOS MODE ENABLED (experimental) ===")
#         time.sleep(random.uniform(0.2, 1.5))

#     # ================================================================
#     #                   MAIN ENTRY
#     # ================================================================
#     def run(self):
#         self.start_servers()
#         self.setup_users()
#         self.run_email_simulation()
#         self.run_pop3_integrity_check()
#         self.stop_servers()


# # ================================================================
# #                    ENTRYPOINT
# # ================================================================
# def main():
#     setup_logger("SIM", level="DEBUG")

#     sim = Simulation(num_users=5, concurrency=5)

#     try:
#         sim.run()
#     except KeyboardInterrupt:
#         print("Simulation interrupted.")
#     finally:
#         sim.stop_servers()


# if __name__ == "__main__":
#     main()

# # import random
# # import time
# # import sys
# # import os
# # import threading

# # # --- Path Setup ---
# # # Ensure we can import 'src' regardless of where this script is run
# # current_dir = os.path.dirname(os.path.abspath(__file__))
# # if os.path.exists(os.path.join(current_dir, "src")):
# #     sys.path.append(current_dir)
# # else:
# #     sys.path.append(os.path.dirname(current_dir))

# # from src.auth.user_manager import UserManager
# # from src.smtp.smtp_client import SMTPClient
# # from src.smtp.smtp_server import SMTPServer
# # from src.pop3.pop3_server import POP3Server
# # from src.config import SMTP_SERVER_HOST, SMTP_SERVER_PORT, POP3_SERVER_HOST, POP3_SERVER_PORT
# # from src.common.logger import setup_logger, get_class_logger


# # class Simulation:
# #     """
# #     Simulates user creation and email sending.
# #     Automatically spins up local SMTP/POP3 servers for the duration of the test.
# #     """

# #     def __init__(self, num_users: int = 5):
# #         self.log = get_class_logger(self)
# #         self.num_users = num_users
# #         self.users = []
# #         self.user_manager = UserManager()

# #         # Server instances
# #         self.smtp_server = None
# #         self.pop3_server = None

# #     def start_servers(self):
# #         """Starts the SMTP and POP3 servers in background threads."""
# #         self.log.info("--- 🚀 STARTING INFRASTRUCTURE ---")

# #         # Initialize Servers
# #         self.smtp_server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
# #         self.pop3_server = POP3Server(POP3_SERVER_HOST, POP3_SERVER_PORT)

# #         # Start them
# #         self.smtp_server.start()
# #         self.pop3_server.start()

# #         # Give them a moment to bind sockets
# #         time.sleep(0.5)
# #         self.log.info("Servers are running in background threads.")

# #     def stop_servers(self):
# #         """Stops the background servers."""
# #         self.log.info("--- 🛑 SHUTTING DOWN INFRASTRUCTURE ---")
# #         if self.smtp_server:
# #             self.smtp_server.stop()
# #         if self.pop3_server:
# #             self.pop3_server.stop()

# #     def setup_users(self):
# #         self.log.info(f"Setting up {self.num_users} simulation users...")
# #         for i in range(1, self.num_users + 1):
# #             username = f"user{i}"
# #             password = "password"

# #             user = self.user_manager.get_user(username)
# #             if not user:
# #                 user = self.user_manager.create_user(username, password)

# #             self.users.append(user)
# #         self.log.info(f"User setup complete: {[u.username for u in self.users]}")

# #     def run_email_simulation(self):
# #         self.log.info("--- 📨 STARTING EMAIL TRAFFIC ---")

# #         if len(self.users) < 2:
# #             self.log.error("Need at least 2 users to run simulation.")
# #             return

# #         for i, sender_user in enumerate(self.users):
# #             # Pick a random recipient
# #             possible_recipients = [u for u in self.users if u.username != sender_user.username]
# #             recipient_user = random.choice(possible_recipients)

# #             sender_email = f"{sender_user.username}@localhost"
# #             recipient_email = f"{recipient_user.username}@localhost"

# #             subject = f"Hello from {sender_user.username}"
# #             body = (
# #                 f"Hi {recipient_user.username},\n\n"
# #                 f"This is simulation message #{i+1} sent via RDT 3.0!\n"
# #                 f"Timestamp: {time.ctime()}\n\n"
# #                 f"Regards,\n{sender_user.username}"
# #             )

# #             self.log.info(f"Attempting: {sender_user.username} -> {recipient_user.username}")

# #             # Retry loop for client socket binding
# #             smtp_client = None
# #             for attempt in range(3):
# #                 try:
# #                     smtp_client = SMTPClient()
# #                     break
# #                 except OSError:
# #                     time.sleep(0.5)

# #             if not smtp_client:
# #                 self.log.error("Could not bind client socket. Skipping.")
# #                 continue

# #             success = smtp_client.send_email(
# #                 sender=sender_email,
# #                 recipient=recipient_email,
# #                 subject=subject,
# #                 body=body,
# #             )

# #             if success:
# #                 self.log.info("✅ Delivery Confirmed.")
# #             else:
# #                 self.log.error("❌ Delivery Failed.")

# #             time.sleep(0.5)


# # def main():
# #     setup_logger("SIM", level="INFO")

# #     # Ensure storage exists
# #     if not os.path.exists("mailboxes"):
# #         os.makedirs("mailboxes")

# #     sim = Simulation(num_users=3)

# #     try:
# #         # 1. Start Servers (The missing step from before)
# #         sim.start_servers()

# #         # 2. Run Logic
# #         sim.setup_users()
# #         sim.run_email_simulation()

# #     except KeyboardInterrupt:
# #         print("\nSimulation aborted.")
# #     finally:
# #         # 3. Cleanup
# #         sim.stop_servers()


# # if __name__ == "__main__":
# #     main()


# # import random
# # import time
# # import sys
# # import os

# # # Add the project root to the Python path
# # sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# # from src.auth.user_manager import UserManager
# # from src.smtp.smtp_client import SMTPClient
# # from src.common.logger import setup_logger, get_class_logger


# # class Simulation:
# #     """
# #     Simulates user creation and email sending.
# #     """

# #     def __init__(self, num_users: int = 5):
# #         """
# #         Initializes the simulation environment.
# #         Args:
# #             num_users: The number of users to simulate.
# #         """
# #         self.log = get_class_logger(self)
# #         self.num_users = num_users
# #         self.users = []
# #         self.user_manager = UserManager()

# #     def setup_users(self):
# #         """
# #         Creates simulation users if they don't already exist.
# #         """
# #         self.log.info(f"Setting up {self.num_users} simulation users...")
# #         for i in range(1, self.num_users + 1):
# #             username = f"user{i}"
# #             password = "password"  # Using a simple password for simulation purposes
# #             user = self.user_manager.get_user(username)
# #             if not user:
# #                 self.log.info(f"User '{username}' not found, creating...")
# #                 user = self.user_manager.create_user(username, password)
# #             else:
# #                 self.log.info(f"User '{username}' already exists.")
# #             self.users.append(user)
# #         self.log.info("User setup complete.")

# #     def run_email_simulation(self):
# #         """
# #         Simulates each user sending an email to another random user.
# #         """
# #         self.log.info("Starting email sending simulation...")
# #         if not self.users:
# #             self.log.error("No users configured for simulation. Run setup_users first.")
# #             return

# #         for sender_user in self.users:
# #             # Ensure the recipient is not the sender
# #             possible_recipients = [u for u in self.users if u.username != sender_user.username]
# #             if not possible_recipients:
# #                 self.log.warning(f"User {sender_user.username} has no one to send an email to.")
# #                 continue

# #             recipient_user = random.choice(possible_recipients)

# #             sender_email = f"{sender_user.username}@localhost"
# #             recipient_email = f"{recipient_user.username}@localhost"

# #             subject = f"Simulation email from {sender_user.username}"
# #             body = (
# #                 f"Hello {recipient_user.username},\n\n"
# #                 f"This is a test email sent at {time.ctime()}\n\n"
# #                 f"From,\n{sender_user.username}"
# #             )

# #             self.log.info(f"Preparing to send email from {sender_email} to {recipient_email}")

# #             smtp_client = SMTPClient()
# #             success = smtp_client.send_email(
# #                 sender=sender_email,
# #                 recipient=recipient_email,
# #                 subject=subject,
# #                 body=body,
# #             )

# #             if success:
# #                 self.log.info(f"Successfully sent email from {sender_email} to {recipient_email}")
# #             else:
# #                 self.log.error(f"Failed to send email from {sender_email} to {recipient_email}")

# #             # A small delay to make the simulation observable and avoid overwhelming the server
# #             time.sleep(1)

# #         self.log.info("Email sending simulation finished.")


# # def main():
# #     """
# #     Main function to run the simulation.
# #     """
# #     # Note: Ensure that the SMTP server is running before starting the simulation.
# #     # You can run the server using: python src/main.py server
# #     setup_logger("SIMULATION", level="INFO")
# #     simulation = Simulation(num_users=5)
# #     simulation.setup_users()
# #     simulation.run_email_simulation()


# # if __name__ == "__main__":
# #     main()
