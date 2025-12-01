"""
Utility script to populate the local database with mock users and emails.

Creates 50 users, then generates emails between random users.
"""

import os
import uuid
import shutil
import json
import random
from datetime import timezone
from email.message import EmailMessage
from email.utils import format_datetime

from faker import Faker

from src.auth.user_manager import UserManager
from src.client.frontend.models.email_data import EmailData
from src.mailbox.mailbox_writer import MailboxWriter
from src.auth.user import User
from src.config import Config

fake = Faker()
TOTAL_USERS = 50
EMAILS_PER_USER = 10  # each user "sends" 10 messages, but delivered to random others


# -----------------------------------------------------------------------------#
# Directory Helpers
# -----------------------------------------------------------------------------#
def ensure_directories():
    """Clean and recreate mailbox + temp directories."""
    for path in (Config.MAILBOXES_DIR, Config.TEMP_EMAILS_DIR):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)


def ensure_users_json():
    """Reset users.json to { 'users': [] }."""
    users_dir = os.path.dirname(Config.USER_DB_FILE)
    os.makedirs(users_dir, exist_ok=True)

    with open(Config.USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": []}, f, indent=2)


# -----------------------------------------------------------------------------#
# Faker Generators
# -----------------------------------------------------------------------------#
def generate_username() -> str:
    return fake.user_name().replace(".", "").replace("_", "").lower()


def generate_password() -> str:
    return fake.password(length=10, special_chars=False)


def build_email(sender_user: User, recipient_user: User) -> EmailData:
    # Generate metadata
    date = fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)
    subject = fake.sentence(nb_words=6)
    body = fake.paragraph(nb_sentences=3)

    # Build sender/receiver addresses
    sender_addr = f"{sender_user.username}@example.com"
    recipient_addr = f"{recipient_user.username}@example.com"

    # Build email message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_addr
    msg["To"] = recipient_addr
    msg["Date"] = format_datetime(date)
    msg.set_content(body)

    # Return EmailData aligned with dataclass ordering
    return EmailData(
        raw_message=msg,
        uid=str(uuid.uuid4()),
        subject=subject,
        sender=sender_addr,
        recipient=recipient_addr,
        date=msg["Date"],
        body_html=None,
        body_text=body,
    )


# -----------------------------------------------------------------------------#
# Main Generator
# -----------------------------------------------------------------------------#
def main():
    ensure_directories()
    ensure_users_json()

    user_manager = UserManager()
    writer = MailboxWriter()

    created_users = 0
    created_messages = 0
    used_usernames = set()

    all_users: list[User] = []
    user_passwords = []

    # -----------------------------------------------------
    # 1. Create all users FIRST
    # -----------------------------------------------------
    for _ in range(TOTAL_USERS):
        username = generate_username()
        while username in used_usernames:
            username = generate_username()
        used_usernames.add(username)

        password = generate_password()

        user = user_manager.create_user(username, password)
        all_users.append(user)
        user_passwords.append((username, password))
        created_users += 1

    # -----------------------------------------------------
    # 2. Generate random emails BETWEEN users
    # -----------------------------------------------------
    for sender in all_users:
        for _ in range(EMAILS_PER_USER):
            recipient = random.choice(all_users)

            # never send to yourself
            while recipient.username == sender.username:
                recipient = random.choice(all_users)

            email_data = build_email(sender, recipient)

            # deliver to recipient mailbox
            if writer.write_email(recipient, email_data):
                created_messages += 1

    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------
    print(f"Users created: {created_users}")
    print(f"Emails written: {created_messages}")
    print(f"Mailboxes dir: {Config.MAILBOXES_DIR}")
    print(f"Users DB file: {Config.USER_DB_FILE}")

    print("\nGenerated usernames + passwords:\n")
    for username, password in user_passwords:
        print(f"{username}: {password}")


if __name__ == "__main__":
    main()
