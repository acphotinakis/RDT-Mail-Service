from src.client.frontend.tui.auth_views import LoginView, SignupView
from src.client.frontend.tui.main_window_rich import MainWindowRich
from src.client.frontend.controllers.auth_controller import AuthController
import src.client.frontend.autologin_manager as autologin_manager
from rich.prompt import Confirm
from src.client.frontend.tui.welcome_view import WelcomeView
from src.common.logger import setup_logger

def run_signup_flow(auth_controller: AuthController):
    """Guides the user through the signup process."""
    signup_view = SignupView()
    while True:
        signup_data = signup_view.run()
        if not signup_data:
            return None  # User cancelled signup

        new_username = signup_data["user"]
        new_password = signup_data["password"]

        if auth_controller.signup(new_username, new_password):
            return new_username, new_password
        else:
            signup_view.error_message = "Signup failed. Username might be taken."


def run_manual_login_flow(auth_controller: AuthController):
    """Handles the manual login process with a 3-strike rule."""
    login_view = LoginView()
    login_attempts = {}
    
    while True:
        login_data = login_view.run()
        if not login_data:
            return None # User cancelled

        current_username, current_password = login_data
        
        login_result = auth_controller.login(current_username, current_password)

        if login_result is True:
            return current_username, current_password # Successful login
        
        elif login_result is False: # Wrong password
            attempts = login_attempts.get(current_username, 0) + 1
            login_attempts[current_username] = attempts

            if attempts >= 3:
                login_view.error_message = "3 failed attempts. You must sign up."
                signup_credentials = run_signup_flow(auth_controller)
                if signup_credentials:
                    return signup_credentials
                else:
                    return None # User cancelled signup
            else:
                remaining = 3 - attempts
                login_view.error_message = f"Invalid password. {remaining} attempts left."

        else: # User not found
            login_view.error_message = "Username not found."


def main():
    """Handles the main application flow: auto-login -> welcome/manual login/signup -> main app."""
    setup_logger("FRONTEND", log_file="frontend.log", level="DEBUG") # Configure frontend logger
    auth_controller = AuthController()
    authenticated_username, authenticated_password = None, None

    # 1. Attempt auto-login
    saved_credentials = autologin_manager.get_saved_credentials()
    if saved_credentials:
        username, password = saved_credentials
        if auth_controller.login(username, password):
            authenticated_username, authenticated_password = username, password
        else:
            # Saved credentials are bad, delete them.
            autologin_manager.delete_credentials()

    # 2. If not auto-logged in, present welcome screen or manual login/signup
    if not authenticated_username:
        welcome_view = WelcomeView()
        while True:
            choice = welcome_view.run()
            if not choice: # User cancelled welcome screen
                return

            if choice == "login":
                credentials = run_manual_login_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break # Authenticated
                else:
                    welcome_view.error_message = "Login failed or cancelled. Please try again." # Or return
            elif choice == "signup":
                credentials = run_signup_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break # Authenticated
                else:
                    welcome_view.error_message = "Signup failed or cancelled. Please try again." # Or return
            
    # 3. Start the main application with the authenticated user
    if authenticated_username and authenticated_password:
        # Ask to save credentials if this was a manual login/signup, not auto-login
        if not saved_credentials:
            remember_me = Confirm.ask("Log in automatically next time?")
            if remember_me:
                autologin_manager.save_credentials(authenticated_username, authenticated_password)

        app = MainWindowRich(authenticated_username, authenticated_password)
        app.run()


if __name__ == "__main__":
    main()
