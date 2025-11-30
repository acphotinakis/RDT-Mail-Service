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
from src.config import MAILBOXES_DIR, TEMP_EMAILS_DIR, USER_DB_FILE
import shutil
import json


# ================================================================
#                 STATISTICS TRACKER
# ================================================================
class SimulationStats:
    """Thread-safe statistics aggregator."""

    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = 0
        self.end_time = 0

        # SMTP Metrics
        self.smtp_attempts = 0
        self.smtp_success = 0
        self.smtp_failed = 0
        self.bytes_sent = 0

        # POP3 Metrics
        self.pop3_verified = 0
        self.pop3_missing = 0

    def start_timer(self):
        self.start_time = time.time()

    def stop_timer(self):
        self.end_time = time.time()

    def record_smtp(self, success: bool, payload_size: int):
        with self.lock:
            self.smtp_attempts += 1
            if success:
                self.smtp_success += 1
                self.bytes_sent += payload_size
            else:
                self.smtp_failed += 1

    def record_pop3(self, verified: bool):
        with self.lock:
            if verified:
                self.pop3_verified += 1
            else:
                self.pop3_missing += 1

    def print_summary(self):
        duration = self.end_time - self.start_time
        if duration <= 0:
            duration = 0.001

        print("\n" + "=" * 60)
        print(f"             SIMULATION RESULTS ({duration:.2f}s)")
        print("=" * 60)
        print(f"SMTP Traffic:")
        print(f"  • Attempts:       {self.smtp_attempts}")
        print(f"  • Success:        {self.smtp_success}")
        print(f"  • Failed:         {self.smtp_failed}")
        print(
            f"  • Success Rate:   {(self.smtp_success/self.smtp_attempts)*100:.1f}%"
            if self.smtp_attempts
            else "  • Success Rate:   N/A"
        )
        print(f"  • Throughput:     {self.smtp_success/duration:.2f} messages/sec")
        print(f"  • Data Volume:    {self.bytes_sent / 1024:.2f} KB")
        print("-" * 60)
        print(f"POP3 Integrity:")
        print(f"  • Verified:       {self.pop3_verified}")
        print(f"  • Missing:        {self.pop3_missing}")
        print("=" * 60 + "\n")


class Simulation:
    def __init__(self, num_users: int = 5, concurrency: int = 5):
        self.log = get_class_logger(self)
        self.num_users = num_users
        self.concurrency = concurrency
        self.users = []
        self.user_manager = UserManager()
        self.stats = SimulationStats()  # Init Stats

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

    # -----------------------------------------------------------------------------#
    # Directory Helpers
    # -----------------------------------------------------------------------------#
    def ensure_directories(self):
        """Clean and recreate mailbox + temp directories."""
        for path in (MAILBOXES_DIR, TEMP_EMAILS_DIR):
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)

    def ensure_users_json(self):
        """Reset users.json to { 'users': [] }."""
        users_dir = os.path.dirname(USER_DB_FILE)
        os.makedirs(users_dir, exist_ok=True)

        with open(USER_DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": []}, f, indent=2)

    # ----------------------------------------------
    # User Setup
    # ----------------------------------------------
    def setup_users(self):
        self.log.info(f"=== PHASE 2: Creating {self.num_users} Users ===")
        self.ensure_directories()
        self.ensure_users_json()
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

            # --- STATS RECORDING ---
            payload_size = len(body) + len(subject)  # Approximate
            self.stats.record_smtp(ok, payload_size)

            if ok:
                self.log.info(f"[SMTP] Delivery OK ({sender_user.username})")
            else:
                self.log.error(f"[SMTP] Delivery FAILED ({sender_user.username})")

        except Exception as e:
            self.stats.record_smtp(False, 0)
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
                        self.stats.record_pop3(True)
                    else:
                        self.log.error(
                            f"  ❌ MISSING: {subject} (Expected in {user.username}'s inbox)"
                        )
                        self.stats.record_pop3(False)

        self.log.info("POP3 verification completed.")

    def run_email_simulation(self):
        self.log.info("=== 📨 PHASE 3: Multi-Threaded Email Traffic ===")

        self.stats.start_timer()  # Start Timer

        threads = []
        for user in self.users:
            t = threading.Thread(target=self._smtp_send_task, args=(user,), daemon=True)
            t.start()
            threads.append(t)
            time.sleep(random.uniform(0.1, 0.3))

        for t in threads:
            t.join()

        self.stats.stop_timer()  # Stop Timer
        self.log.info("SMTP concurrency simulation finished.")

    def run(self):
        self.start_servers()
        self.setup_users()
        self.run_email_simulation()
        # Wait a moment for server to flush to disk
        time.sleep(1.0)
        self.run_pop3_integrity_check()
        self.stop_servers()

        # Print Final Stats
        self.stats.print_summary()


def main():
    setup_logger("SIM", level="INFO")

    if not os.path.exists("mailboxes"):
        os.makedirs("mailboxes")

    sim = Simulation(num_users=500, concurrency=100)

    try:
        sim.run()
    except KeyboardInterrupt:
        print("Simulation interrupted.")
    finally:
        sim.stop_servers()


if __name__ == "__main__":
    main()
