from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListView, QStatusBar
from PySide6.QtGui import QKeySequence, QShortcut

from src.client.frontend.views import MessageView
from src.client.frontend.controllers import AppController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gmail Clone")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel (sidebar and email list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        button_bar = QHBoxLayout()
        self.compose_button = QPushButton("COMPOSE")
        self.reply_button = QPushButton("Reply")
        self.reply_all_button = QPushButton("Reply All")
        self.delete_button = QPushButton("Delete")
        button_bar.addWidget(self.compose_button)
        button_bar.addWidget(self.reply_button)
        button_bar.addWidget(self.reply_all_button)
        button_bar.addWidget(self.delete_button)
        
        self.email_list_view = QListView()
        left_layout.addLayout(button_bar)
        left_layout.addWidget(self.email_list_view)

        # Right panel (message view)
        self.message_view = MessageView()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.message_view, 3)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        
        self.settings_button = QPushButton("Settings")
        self.refresh_button = QPushButton("Refresh")
        self.status_bar.addPermanentWidget(self.settings_button)
        self.status_bar.addPermanentWidget(self.refresh_button)

        # Controller
        self.controller = AppController(self)

        # Keyboard Shortcuts
        self._create_shortcuts()

    def _create_shortcuts(self):
        """Create and connect keyboard shortcuts."""
        # Compose New Email: Ctrl+N
        compose_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        compose_shortcut.activated.connect(self.controller.on_compose_button_clicked)

        # Refresh Inbox: F5
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.controller.on_refresh_clicked)
        
        # Reply: Ctrl+R
        reply_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        reply_shortcut.activated.connect(self.controller.on_reply_clicked)

        # Delete: Del
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.controller.on_delete_clicked)
