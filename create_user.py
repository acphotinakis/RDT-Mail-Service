import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "email-network-service"))
sys.path.insert(0, project_root)

from src.auth.user_manager import UserManager

def main():
    """
    A simple script to create a new user.
    """
    username = input("Enter username: ")
    password = input("Enter password: ")

    if not username or not password:
        print("Username and password cannot be empty.")
        return

    try:
        user_manager = UserManager()
        user_manager.create_user(username, password)
        print(f"User '{username}' created successfully.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
