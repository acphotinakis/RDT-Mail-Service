import sys
import os

# Add the project root to the Python path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from src.client.frontend.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Load QSS theme
    try:
        with open(
            "email-network-service/src/client/frontend/assets/theme.qss", "r"
        ) as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Stylesheet not found. Please check the path.")
        # Or handle it more gracefully

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
