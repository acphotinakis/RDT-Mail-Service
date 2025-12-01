import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from src.client.frontend.gui_qt.auth_views_qt import LoginDialog, SignupDialog
from src.client.frontend.gui_qt.main_window_qt import MainWindowQt
from src.client.frontend.gui_qt.welcome_view_qt import WelcomeDialog
from src.client.frontend.controllers.auth_controller import AuthController
import src.client.frontend.autologin_manager as autologin_manager
from src.common.logger import setup_logger, get_class_logger


log = get_class_logger("RUN_FRONTEND")


def run_signup_flow(auth_controller: AuthController):
    """Guides the user through the signup process."""
    log.info("Starting signup flow.")
    error = None
    while True:
        signup_view = SignupDialog(error_message=error)
        signup_data = signup_view.get_data()
        if not signup_data:
            log.info("User cancelled signup flow.")
            return None  # User cancelled signup

        new_username = signup_data["user"]
        new_password = signup_data["password"]

        log.info(f"Attempting to sign up new user: {new_username}")
        if auth_controller.signup(new_username, new_password):
            log.info("Signup successful.")
            return new_username, new_password
        else:
            error = "Signup failed. Username might be taken."
            log.warning(f"Signup failed for user: {new_username}. Reason: {error}")


def run_manual_login_flow(auth_controller: AuthController):
    """Handles the manual login process with a 3-strike rule."""
    log.info("Starting manual login flow.")
    login_attempts: dict[str, int] = {}

    while True:
        login_view = LoginDialog(error_message=None)
        login_data = login_view.get_data()
        if not login_data:
            log.info("User cancelled manual login flow.")
            return None  # User cancelled

        current_username, current_password = login_data
        log.info(f"Processing manual login for user: {current_username}")

        login_result = auth_controller.login(current_username, current_password)

        if login_result is True:
            log.info("Manual login successful.")
            return current_username, current_password  # Successful login

        elif login_result is False:  # Wrong password
            attempts = login_attempts.get(current_username, 0) + 1
            login_attempts[current_username] = attempts
            log.warning(f"Invalid password for {current_username}. Attempt {attempts}/3.")

            if attempts >= 3:
                log.warning("Login failed after 3 attempts. Triggering signup flow.")
                signup_credentials = run_signup_flow(auth_controller)
                if signup_credentials:
                    return signup_credentials
                else:
                    return None  # User cancelled signup
            else:
                remaining = 3 - attempts
                QMessageBox.critical(
                    None, "Login Failed", f"Invalid password. {remaining} attempts left."
                )

        else:  # User not found
            log.warning(f"Login failed: User '{current_username}' not found.")
            QMessageBox.critical(None, "Login Failed", "Username not found.")


def run_frontend():
    """Handles the main application flow: auto-login -> welcome/manual login/signup -> main app."""
    setup_logger("FRONTEND", log_file="frontend.log", level="DEBUG")  # Configure frontend logger
    log.info("--- Starting Frontend Application ---")
    qt_app = QApplication(sys.argv)
    auth_controller = AuthController()
    authenticated_username, authenticated_password = None, None

    # 1. Attempt auto-login
    log.info("Attempting auto-login...")
    saved_credentials = autologin_manager.get_saved_credentials()
    if saved_credentials:
        username, password = saved_credentials
        if auth_controller.login(username, password):
            log.info("Auto-login successful.")
            authenticated_username, authenticated_password = username, password
        else:
            log.warning("Auto-login failed with saved credentials. Deleting them.")
            autologin_manager.delete_credentials()

    # 2. If not auto-logged in, present welcome screen or manual login/signup
    if not authenticated_username:
        log.info("No authenticated user. Starting welcome screen flow.")
        while True:
            welcome_view = WelcomeDialog()
            choice = welcome_view.get_choice()
            if not choice:
                log.info("User cancelled at welcome screen. Exiting.")
                return

            if choice == "login":
                credentials = run_manual_login_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break
                else:
                    continue
            elif choice == "signup":
                credentials = run_signup_flow(auth_controller)
                if credentials:
                    authenticated_username, authenticated_password = credentials
                    break
                else:
                    continue

    # 3. Start the main application with the authenticated user
    if authenticated_username and authenticated_password:
        log.info(
            f"Authentication complete. Starting main window for user '{authenticated_username}'."
        )
        main_window = MainWindowQt(authenticated_username, authenticated_password)
        main_window.show()

        if not saved_credentials:
            log.debug("Prompting user to save credentials for auto-login.")
            remember_me = QMessageBox.question(
                main_window,
                "Remember Me",
                "Log in automatically next time?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if remember_me == QMessageBox.StandardButton.Yes:
                log.info("User chose to save credentials.")
                autologin_manager.save_credentials(authenticated_username, authenticated_password)
            else:
                log.info("User chose not to save credentials.")

        qt_app.exec()
        log.info("--- Frontend Application Shutdown ---")
    else:
        log.warning("Authentication failed or was cancelled. Application will not start.")


if __name__ == "__main__":
    run_frontend()
