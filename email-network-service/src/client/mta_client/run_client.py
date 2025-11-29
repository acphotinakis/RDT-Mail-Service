from rich.console import Console
from rich.table import Table

console = Console()

console.print("[bold blue]Welcome to my pretty terminal app![/bold blue]")

table = Table(title="My Data")
table.add_column("Name", style="cyan")
table.add_column("Age", style="magenta")
table.add_row("Alice", "30")
table.add_row("Bob", "25")
console.print(table)
