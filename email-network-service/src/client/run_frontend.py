import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from src.client.frontend.gui_qt.auth_views_qt import LoginDialog, SignupDialog
from src.client.frontend.gui_qt.main_window_qt import MainWindowQt
from src.client.frontend.gui_qt.welcome_view_qt import WelcomeDialog
from src.client.frontend.controllers.auth_controller import AuthController
import src.client.frontend.autologin_manager as autologin_manager
from src.common.logger import setup_logger

def run_signup_flow(auth_controller: AuthController):
    """Guides the user through the signup process."""
    error = None
    while True:
        signup_view = SignupDialog(error_message=error)
        signup_data = signup_view.get_data()
        if not signup_data:
            return None  # User cancelled signup

        new_username = signup_data["user"]
        new_password = signup_data["password"]

        if auth_controller.signup(new_username, new_password):
            return new_username, new_password
        else:
            error = "Signup failed. Username might be taken."


def run_manual_login_flow(auth_controller: AuthController):
    """Handles the manual login process with a 3-strike rule."""
    login_attempts = {}
    
    while True:
        login_view = LoginDialog(error_message=None)
        login_data = login_view.get_data()
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
                signup_credentials = run_signup_flow(auth_controller)
                if signup_credentials:
                    return signup_credentials
                else:
                    return None # User cancelled signup
            else:
                remaining = 3 - attempts
                QMessageBox.critical(None, "Login Failed", f"Invalid password. {remaining} attempts left.")

        else: # User not found
            QMessageBox.critical(None, "Login Failed", "Username not found.")


def main():
    """Handles the main application flow: auto-login -> welcome/manual login/signup -> main app."""
    setup_logger("FRONTEND", log_file="frontend.log", level="DEBUG") # Configure frontend logger
    qt_app = QApplication(sys.argv)
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
        while True:
            welcome_view = WelcomeDialog()
            choice = welcome_view.get_choice()
            if not choice: # User cancelled welcome screen
                return

            if choice == "login":
                credentials = run_manual_login_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break # Authenticated
                else:
                    continue
            elif choice == "signup":
                credentials = run_signup_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break # Authenticated
                else:
                    continue
            
    # 3. Start the main application with the authenticated user
    if authenticated_username and authenticated_password:
        main_window = MainWindowQt(authenticated_username, authenticated_password)
        main_window.show()

        # Ask to save credentials if this was a manual login/signup, not auto-login
        if not saved_credentials:
            remember_me = QMessageBox.question(
                main_window,
                "Remember Me",
                "Log in automatically next time?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if remember_me == QMessageBox.Yes:
                autologin_manager.save_credentials(authenticated_username, authenticated_password)

        qt_app.exec()


if __name__ == "__main__":
    main()
