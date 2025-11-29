"""
Utility script to populate the local database with mock users and emails.

Creates 50 users with Faker-generated usernames + passwords.
Each user gets 10 emails with Faker-generated realistic content.
Also regenerates database/users.json from scratch.
"""

import os
import uuid
import shutil
import json
from datetime import timezone
from email.message import EmailMessage
from email.utils import format_datetime

from faker import Faker

from src.auth.user_manager import UserManager
from src.client.frontend.models.email_data import EmailData
from src.mailbox.mailbox_writer import MailboxWriter
from src.auth.user import User
from src.common.config import MAILBOXES_DIR, TEMP_EMAILS_DIR, USER_DB_FILE

fake = Faker()
TOTAL_USERS = 50
EMAILS_PER_USER = 10


# -----------------------------------------------------------------------------#
# Directory Helpers
# -----------------------------------------------------------------------------#
def ensure_directories():
    """Clean and recreate mailbox + temp directories."""
    for path in (MAILBOXES_DIR, TEMP_EMAILS_DIR):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)


def ensure_users_json():
    """Reset users.json to { 'users': [] }."""
    users_dir = os.path.dirname(USER_DB_FILE)
    os.makedirs(users_dir, exist_ok=True)

    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": []}, f, indent=2)


# -----------------------------------------------------------------------------#
# Faker Generators
# -----------------------------------------------------------------------------#


def generate_username() -> str:
    """Generate a filesystem-safe unique username."""
    return fake.user_name().replace(".", "").replace("_", "").lower()


def generate_password() -> str:
    """Generate a Faker password (10 char alphanumeric)."""
    return fake.password(length=10, special_chars=False)


def build_email(username: str) -> EmailData:
    """Build a realistic mock email using Faker."""
    date = fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)

    subject = fake.sentence(nb_words=6)
    sender = fake.email()
    recipient = f"{username}@example.com"
    body = fake.paragraph(nb_sentences=3)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg["Date"] = format_datetime(date)
    msg.set_content(body)

    return EmailData(
        raw_message=msg,
        uid=str(uuid.uuid4()),
        subject=subject,
        sender=sender,
        recipient=recipient,
        date=msg["Date"],
        body_text=body,
        body_html=None,
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
    user_passwords = []

    for _ in range(TOTAL_USERS):
        # Generate unique username
        username = generate_username()
        while username in used_usernames:
            username = generate_username()
        used_usernames.add(username)

        password = generate_password()

        # Create user in the DB
        try:
            user = user_manager.create_user(username, password)
            created_users += 1
        except ValueError:
            # Already exists? Fetch
            user = user_manager.get_user(username) or User(username, password)

        user_passwords.append((username, user.password))

        # Create mailbox emails
        for _ in range(EMAILS_PER_USER):
            email_data = build_email(username)
            if writer.write_email(user, email_data):
                created_messages += 1

    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------
    print(f"Users created: {created_users}")
    print(f"Emails written: {created_messages}")
    print(f"Mailboxes dir: {MAILBOXES_DIR}")
    print(f"Users DB file: {USER_DB_FILE}")

    print("\nGenerated usernames + passwords:\n")
    for username, password in user_passwords:
        print(f"{username}: {password}")


if __name__ == "__main__":
    main()
