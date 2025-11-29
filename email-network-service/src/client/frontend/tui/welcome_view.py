from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


class WelcomeView:
    """
    A view that presents the user with options to Login or Sign Up.
    """

    def __init__(self):
        self.error_message = None

    def run(self) -> str | None:
        """
        Presents the choice and returns "login", "signup", or None if cancelled.
        """
        while True:
            console.clear()
            title = "[bold cyan]Welcome to the Email Client[/bold cyan]"
            if self.error_message:
                title += f"\n[red]{self.error_message}[/red]"
            console.print(Panel(title, width=60))

            choice = Prompt.ask(
                "Do you want to [bold]login[/bold] or [bold]signup[/bold]?",
                choices=["login", "signup"],
                default="login",
            ).lower()

            if choice in ["login", "signup"]:
                return choice
            else:
                self.error_message = "Invalid choice. Please enter 'login' or 'signup'."
