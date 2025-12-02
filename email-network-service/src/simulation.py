"""
===============================================================
         ADVANCED NETWORKED EMAIL SYSTEM SIMULATION
===============================================================
"""

import sys
import random
import time
import sys
import os
import threading
import traceback
import argparse
from concurrent.futures import ThreadPoolExecutor

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
from src.config import Config
from src.common.logger import setup_logger, get_class_logger

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
    def __init__(self, num_users, num_emails, concurrency, delay_between_sends, message_size):
        self.log = get_class_logger(self)

        self.num_users = num_users
        self.num_emails = num_emails
        self.concurrency = concurrency
        self.delay_between_sends = delay_between_sends
        self.message_size = message_size

        self.users = []
        self.user_manager = UserManager()
        self.stats = SimulationStats()
        self.smtp_server = None
        self.pop3_server = None
        self.sent_messages = []
        self.log.info(self.to_string())

    # ----------------------------------------------
    # Infrastructure Management
    # ----------------------------------------------
    def start_servers(self):
        self.log.info("=== PHASE 1: STARTING INFRASTRUCTURE ===")

        self.log.info("Starting SMTP server...")

        self.smtp_server = SMTPServer(Config.SMTP_SERVER_HOST, Config.SMTP_SERVER_PORT)
        self.pop3_server = POP3Server(Config.POP3_SERVER_HOST, Config.POP3_SERVER_PORT)

        self.smtp_server.start()
        self.pop3_server.start()

        # Allow sockets to bind
        time.sleep(1.0)
        self.log.info("SMTP + POP3 servers running.")

    def stop_servers(self):
        self.log.info("=== SHUTDOWN INFRASTRUCTURE ===")
        if self.smtp_server:
            self.smtp_server.stop()
        if self.pop3_server:
            self.pop3_server.stop()

    # -----------------------------------------------------------------------------#
    # Directory Helpers
    # -----------------------------------------------------------------------------#
    def setup_directories(self):
        self.ensure_directories()
        self.ensure_users_json()

    def ensure_directories(self):
        """Clean and recreate mailbox + temp directories."""
        for path in (Config.MAILBOXES_DIR, Config.TEMP_EMAILS_DIR):
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)

    def ensure_users_json(self):
        """Reset users.json to { 'users': [] }."""
        users_dir = os.path.dirname(Config.USER_DB_FILE)
        os.makedirs(users_dir, exist_ok=True)

        with open(Config.USER_DB_FILE, "w", encoding="utf-8") as f:
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
        self.log.info("=== PHASE 4: POP3 Consistency Verification ===")

        def extract_subject(raw_text):
            for line in raw_text.splitlines():
                if line.lower().startswith("subject:"):
                    return line[8:].strip()
            return ""

        for user in self.users:
            self.log.info(f"[POP3] Checking mailbox of {user.username}")

            client = POP3Client()
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
        self.log.info(
            f"=== PHASE 3: Multi-Threaded Email Traffic STARTED ===\n"
            f"Concurrency Level     : {self.concurrency}\n"
            f"Users Participating    : {len(self.users)}\n"
            f"Delay Between Sends    : {self.delay_between_sends}s\n"
            f"Total Email Targets    : {self.num_users} users\n"
            f"Message Size (approx.) : {self.message_size} bytes\n"
            "-------------------------------------------------------"
        )

        self.stats.start_timer()
        start_timestamp = time.time()

        # Create the pool
        self.log.info("[SIM] Allocating ThreadPoolExecutor...")
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = []

            self.log.info(
                f"[SIM] ThreadPoolExecutor READY — Max Workers = {self.concurrency}\n"
                f"[SIM] Dispatching SMTP tasks..."
            )

            # ----------------------------------------------------------------------
            # DISPATCH SMTP SENDING TASKS — NOW RESPECTS num_emails EVEN IF num_users IS SMALL
            # ----------------------------------------------------------------------
            task_id = 1
            total_tasks = len(self.users) * self.num_emails

            for user in self.users:
                for i in range(self.num_emails):
                    self.log.info(
                        f"[SIM] QUEUING TASK {task_id}/{total_tasks} — "
                        f"user '{user.username}', email #{i+1}/{self.num_emails}"
                    )

                    future = pool.submit(self._smtp_send_task, user)
                    futures.append(future)

                    task_id += 1

                    # Optional staggering
                    if self.delay_between_sends > 0:
                        self.log.debug(
                            f"[SIM] Delaying next task for {self.delay_between_sends:.3f} seconds..."
                        )
                        time.sleep(self.delay_between_sends)

            self.log.info(
                "[SIM] All tasks submitted to ThreadPoolExecutor — awaiting completion..."
            )

            # ----------------------------------------------------------------------
            # WAIT FOR ALL TASKS TO FINISH
            # ----------------------------------------------------------------------
            completed = 0
            total = len(futures)

            for future in futures:
                try:
                    future.result()  # Block until the thread completes
                    completed += 1
                    self.log.info(
                        f"[SIM] Task Completion Progress: {completed}/{total} "
                        f"({(completed/total)*100:.1f}%)"
                    )
                except Exception as e:
                    self.log.error(
                        f"[SIM] ERROR: Exception while executing SMTP task.\n"
                        f"Reason: {e}\n"
                        "Traceback follows:",
                        exc_info=True,
                    )

        # ----------------------------------------------------------------------
        # FINISH / CLEANUP
        # ----------------------------------------------------------------------
        self.stats.stop_timer()
        total_time = time.time() - start_timestamp

        self.log.info(
            f"=== PHASE 3 COMPLETE: Multi-Threaded SMTP Simulation Finished ===\n"
            f"Total Users Processed  : {len(self.users)}\n"
            f"Concurrency Level      : {self.concurrency}\n"
            f"Total Execution Time   : {total_time:.3f}s\n"
            f"Avg Throughput         : {self.stats.smtp_success / total_time:.2f} msg/sec\n"
            f"--------------------------------------------------------------"
        )

    # def run_email_simulation(self):
    #     self.log.info("=== PHASE 3: Multi-Threaded Email Traffic ===")

    #     # start timer
    #     self.stats.start_timer()

    #     threads = []
    #     for user in self.users:
    #         t = threading.Thread(target=self._smtp_send_task, args=(user,), daemon=True)
    #         t.start()
    #         threads.append(t)
    #         time.sleep(random.uniform(0.1, 0.3))

    #     for t in threads:
    #         t.join()

    #     self.stats.stop_timer()  # Stop Timer
    #     self.log.info("SMTP concurrency simulation finished.")

    def run(self):
        self.setup_users()
        self.start_servers()
        self.run_email_simulation()
        # Wait a moment for server to flush to disk
        time.sleep(3.0)
        sys.exit(0)
        self.run_pop3_integrity_check()
        self.stop_servers()

        # Print Final Stats
        self.stats.print_summary()

    def to_string(self) -> str:
        """
        Returns a detailed diagnostic overview of the Simulation environment,
        configuration, internal state, and runtime components.
        """

        props = {
            # --- Simulation Config ---
            "Num Users": self.num_users,
            "Num Emails/User": self.num_emails,
            "Concurrency": self.concurrency,
            "Delay Between Sends": self.delay_between_sends,
            "Message Size": self.message_size,
            # --- Internal Structures ---
            "Users Loaded": len(self.users),
            "Usernames": ", ".join(u.username for u in self.users) if self.users else "(none)",
            "Sent Messages (Recorded)": len(self.sent_messages),
            # --- Subsystems ---
            "User Manager": self.user_manager.__class__.__name__,
            "Stats Tracker": self.stats.__class__.__name__,
            "SMTP Server": (
                f"{self.smtp_server.__class__.__name__} @ "
                f"{self.smtp_server.host}:{self.smtp_server.port}"
                if self.smtp_server
                else "(not started)"
            ),
            "POP3 Server": (
                f"{self.pop3_server.__class__.__name__} @ "
                f"{self.pop3_server.host}:{self.pop3_server.port}"
                if self.pop3_server
                else "(not started)"
            ),
            # --- Singleton Info ---
            "Instance Address": hex(id(self)),
        }

        # Compute alignment width
        longest = max(len(k) for k in props.keys())
        lines = ["\nSimulation State:"]
        lines.append("-" * (longest + 30))

        for k, v in props.items():
            lines.append(f"{k.ljust(longest)} : {v}")

        lines.append("-" * (longest + 30))
        return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Email Network Simulation")

    parser.add_argument(
        "--num_users", type=int, default=10, help="Number of users to create (default: 10)"
    )
    parser.add_argument(
        "--num_emails",
        type=int,
        default=5,
        help="Number of emails each user will send (default: 5)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Max concurrent sending threads (default: 5)"
    )
    parser.add_argument(
        "--delay_between_sends",
        type=float,
        default=0.2,
        help="Delay between launching send threads (default: 0.2)",
    )
    parser.add_argument(
        "--message_size",
        type=int,
        default=200,
        help="Approximate message size in bytes (default: 200)",
    )

    return parser.parse_args()


def main():
    setup_logger(
        name="EMAIL_NETWORK_SERVICE <--> SIMULATION",
        level="INFO",
        log_file="email_network_service.log",
    )

    args = parse_args()
    Config.apply_args(args)
    Config.log_config()

    sim = Simulation(
        num_users=Config.NUM_USERS,
        num_emails=Config.NUM_EMAILS_PER_USER,
        concurrency=Config.CONCURRENCY,
        delay_between_sends=Config.DELAY_BETWEEN_SENDS,
        message_size=Config.MESSAGE_SIZE,
    )

    sim.to_string()

    try:
        sim.run()
    except KeyboardInterrupt:
        print("Simulation interrupted.")
    finally:
        sim.stop_servers()


if __name__ == "__main__":
    main()
