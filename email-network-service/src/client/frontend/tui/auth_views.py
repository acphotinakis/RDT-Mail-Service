from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()


class LoginView:
    """Rich Terminal UI Login View"""

    def __init__(self):
        self.error_message = None

    def run(self) -> tuple[str, str] | None:
        """
        Returns (username, password)
        or None if user cancels.
        """

        while True:
            console.clear()

            title = "[bold cyan]Login[/bold cyan]"
            if self.error_message:
                title += f"\n[red]{self.error_message}[/red]"

            console.print(Panel(title, width=60))

            username = Prompt.ask("Username")
            password = Prompt.ask("Password")

            if not username or not password:
                self.error_message = "Both fields are required."
                continue

            return username, password


class SignupView:
    """Rich Terminal UI Signup View"""

    def __init__(self):
        self.error_message = None

    def run(self) -> dict | None:
        """
        Returns dict: {"user": username, "password": password}
        or None if cancelled.
        """

        while True:
            console.clear()

            title = "[bold green]Create New Account[/bold green]"
            if self.error_message:
                title += f"\n[red]{self.error_message}[/red]"

            console.print(Panel(title, width=60))

            username = Prompt.ask("Choose Username")
            password = Prompt.ask("Choose Password", password=True)
            confirm = Prompt.ask("Confirm Password", password=True)

            if not username or not password or not confirm:
                self.error_message = "All fields are required."
                continue

            if password != confirm:
                self.error_message = "Passwords do not match."
                continue

            return {"user": username, "password": password}
