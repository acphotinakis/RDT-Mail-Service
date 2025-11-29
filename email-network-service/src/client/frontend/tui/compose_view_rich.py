from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from typing import Optional, Dict

console = Console()


class ComposeView:
    """Rich compose window."""

    def __init__(self, initial_data: Optional[Dict[str, str]] = None):
        self.initial_data = initial_data or {}

    def run(self) -> Optional[Dict[str, str]]:
        console.clear()
        console.print(Panel("Compose New Email", style="bold green"))

        recipient = Prompt.ask("To", default=self.initial_data.get("recipient"))
        subject = Prompt.ask("Subject", default=self.initial_data.get("subject"))

        console.print("Body (type 'EOF' to finish):")
        body_lines = []
        initial_body = self.initial_data.get("body")
        if initial_body:
            console.print(initial_body)
            body_lines.append(initial_body)

        while True:
            line = Prompt.ask("")
            if line.strip().upper() == "EOF":
                break
            body_lines.append(line)

        body = "\n".join(body_lines)

        if not recipient or not subject:
            console.print("[red]Recipient and subject required.[/red]")
            return None

        return {"recipient": recipient, "subject": subject, "body": body}
