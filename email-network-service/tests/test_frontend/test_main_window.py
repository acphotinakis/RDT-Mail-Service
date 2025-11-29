import sys
from unittest.mock import MagicMock, patch

# Mock the PySide6 modules since they are not installed
MOCK_MODULES = {
    "PySide6.QtCore": MagicMock(),
    "PySide6.QtWidgets": MagicMock(),
    "PySide6.QtWebEngineWidgets": MagicMock(),
}
patcher = patch.dict("sys.modules", MOCK_MODULES)
patcher.start()

# Now we can import the application modules
from client.frontend.main_window import MainWindow
from client.frontend.models import EmailListModel, EmailData
from email.message import Message


def test_main_window_creation(qtbot):
    """Test if the main window is created without errors."""

    # Patch the controller to prevent it from running real logic
    with patch("src.client.frontend.main_window.AppController") as MockController:
        MockController.return_value.load_user_emails = MagicMock()

        window = MainWindow()
        qtbot.addWidget(window)

        assert window.windowTitle() == "Gmail Clone"
        assert window.email_list_view is not None
        assert window.message_view is not None
        assert window.compose_button.text() == "COMPOSE"
        assert window.refresh_button.text() == "Refresh"


def test_email_model_loading(qtbot):
    """Test that the controller can load emails into the model."""

    with patch("src.client.frontend.main_window.AppController") as MockController:
        # We create a real model to test its interaction
        model = EmailListModel()

        # Make the mocked controller use our real model
        instance = MockController.return_value
        instance.email_model = model

        # Create the window, which initializes the (mocked) controller
        window = MainWindow()
        qtbot.addWidget(window)

        # Simulate the controller loading emails
        dummy_emails = [
            EmailData("1", "Sub1", "a@a.com", "b@b.com", "date1", raw_message=Message()),
            EmailData("2", "Sub2", "c@c.com", "d@d.com", "date2", raw_message=Message()),
        ]
        model.update_emails(dummy_emails)

        # Check if the model has the correct number of rows
        assert model.rowCount(None) == 2


# Stop patching after all tests in this module are done
def teardown_module(module):
    patcher.stop()
