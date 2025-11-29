from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.text import Text
from rich.prompt import Prompt  # Import Prompt
from typing import List, Optional

from src.client.frontend.tui.message_view_rich import MessageView
from src.client.frontend.tui.compose_view_rich import ComposeView
from src.client.frontend.controllers.app_controller_rich import AppController, ViewInterface
from src.client.frontend.models.email_data import EmailData
from src.common.logger import get_class_logger  # Only import get_class_logger

console = Console()


class MainWindowRich(ViewInterface):
    """
    Terminal-based UI for the email client using Rich.
    """

    def __init__(self, username: str, password: str):
        # Initialize internal state FIRST
        self.emails: List[EmailData] = []
        self.selected_email_index: Optional[int] = None
        self.status_message = "Ready"
        self.layout = self._build_layout()
        self.refresh_enabled = True
        self.log = get_class_logger(self)  # Initialize logger for this class

        # Now create the controller, which may call back to the view
        self.controller = AppController(self, username, password)

    def _build_layout(self) -> Layout:
        """Builds the initial layout for the TUI."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer"),
        )
        layout["main"].split_row(Layout(name="side"), Layout(name="body", ratio=2))
        layout["side"].split(Layout(name="email_list"))
        return layout

    def _render_header(self) -> Panel:
        """Renders the top header with action keys."""
        button_text = (
            "[bold green](c)[/bold green]ompose | "
            "[bold yellow](r)[/bold yellow]eply | "
            "[bold red](d)[/bold red]elete | "
            "[bold blue](f)[/bold blue]resh | "
            "[bold cyan](s)[/bold cyan]ettings | "
            "[bold purple](l)[/bold purple]ogout | "
            "[bold](q)[/bold]uit"
        )
        return Panel(Align.center(button_text), title="Actions")

    def _render_email_list(self) -> Panel:
        """Renders the list of emails in a table."""
        table = Table(expand=True)
        table.add_column("ID", width=3)
        table.add_column("From", style="cyan")
        table.add_column("Subject", style="magenta")

        for i, email in enumerate(self.emails):
            style = "reverse" if i == self.selected_email_index else ""
            table.add_row(str(i + 1), email.sender, email.subject, style=style)

        return Panel(table, title="Inbox")

    def _refresh_layout(self):
        """Updates the dynamic parts of the layout."""
        self.layout["header"].update(self._render_header())
        self.layout["side"].update(self._render_email_list())
        self.layout["footer"].update(Panel(Text(self.status_message, justify="left")))

    def run(self):
        """Main TUI loop."""
        self.controller.load_user_emails(self.controller.user)
        self.layout["body"].update(Panel("No message selected.", title="Message"))

        live = Live(self.layout, console=console, screen=True, refresh_per_second=4)

        try:
            live.start()
            while True:
                self._refresh_layout()
                cmd = Prompt.ask("[bold]Action[/bold]").strip().lower()
                self.log.debug(f"Command entered: {cmd}")  # Log command

                if cmd.isdigit():
                    index = int(cmd) - 1
                    if 0 <= index < len(self.emails):
                        self.selected_email_index = index
                        self.controller.select_email(index)
                elif cmd in ("c", "compose"):
                    self.log.debug("Stopping live display for compose.")
                    live.stop()
                    self.open_compose_window()
                    self._refresh_layout()
                    live.start(refresh=True)
                    self.log.debug("Resuming live display after compose.")
                elif cmd in ("r", "reply"):
                    if self.selected_email_index is not None:
                        self.log.debug("Stopping live display for reply.")
                        live.stop()
                        self.controller.reply_to_email(self.selected_email_index)
                        self._refresh_layout()
                        live.start(refresh=True)
                        self.log.debug("Resuming live display after reply.")
                elif cmd in ("d", "delete"):
                    if self.selected_email_index is not None:
                        self.controller.delete_email(self.selected_email_index)
                elif cmd in ("f", "fresh"):
                    self.controller.refresh_emails()
                elif cmd in ("s", "settings"):
                    self.controller.open_settings()
                elif cmd in ("l", "logout"):
                    self.logout()
                    break
                elif cmd in ("q", "quit"):
                    break
        finally:
            live.stop()

    # ========== ViewInterface Methods ==========

    def display_emails(self, emails: List[EmailData]):
        self.emails = emails
        if self.selected_email_index is not None and self.selected_email_index >= len(emails):
            self.selected_email_index = None
            self.clear_email_content()

    def display_email_content(self, html_content: str):
        self.layout["body"].update(Panel(MessageView.render_html(html_content), title="Message"))

    def show_status_message(self, message: str):
        self.status_message = message

    def open_compose_window(self, initial_data: Optional[dict] = None):
        compose_view = ComposeView(initial_data)
        email_data = compose_view.run()
        if email_data:
            self.controller.send_email(email_data)

    def clear_email_content(self):
        self.layout["body"].update(Panel("No message selected.", title="Message"))

    def enable_refresh_button(self, enabled: bool):
        self.refresh_enabled = enabled

    def run_on_ui_thread(self, func, *args, **kwargs):
        """Rich TUI is synchronous, so execute immediately."""
        func(*args, **kwargs)

    def logout(self):
        self.controller.logout()
