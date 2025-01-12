"""Monitor command for nova CLI."""

import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from nova.cli.utils.command import NovaCommand

logger = logging.getLogger(__name__)


class MonitorCommand(NovaCommand):
    """Monitor command for system health, stats, and logs."""

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments

        Raises:
            KeyError: If required arguments are missing
        """
        if not kwargs:
            raise KeyError("No subcommand provided")

        subcommand = kwargs.get("subcommand")
        if subcommand == "health":
            self.run_health()
        elif subcommand == "stats":
            self.run_stats()
        elif subcommand == "logs":
            self.run_logs()
        else:
            raise KeyError(f"Unknown subcommand: {subcommand}")

    def run_health(self) -> None:
        """Run health check."""
        console = Console()
        table = Table(title="System Health")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Path", style="blue")

        # Check .nova directory
        nova_dir = Path(".nova")
        nova_status = "✓ OK" if nova_dir.exists() else "✗ Missing"
        table.add_row(".nova Directory", nova_status, str(nova_dir.absolute()))

        # Check vector store
        vector_store = nova_dir / "vectorstore"
        vector_status = "✓ OK" if vector_store.exists() else "✗ Missing"
        table.add_row("Vector Store", vector_status, str(vector_store.absolute()))

        # Check logs directory
        logs_dir = nova_dir / "logs"
        logs_status = "✓ OK" if logs_dir.exists() else "✗ Missing"
        table.add_row("Logs Directory", logs_status, str(logs_dir.absolute()))

        console.print(table)

    def run_stats(self) -> None:
        """Run stats command."""
        console = Console()
        table = Table(title="System Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Count vector embeddings
        vector_store = Path(".nova/vectorstore")
        if vector_store.exists():
            embedding_count = len(list(vector_store.glob("*.npy")))
        else:
            embedding_count = 0
        table.add_row("Vector Embeddings", str(embedding_count))

        # Count processed notes
        notes_dir = Path(".nova/notes")
        if notes_dir.exists():
            note_count = len(list(notes_dir.glob("*.json")))
        else:
            note_count = 0
        table.add_row("Processed Notes", str(note_count))

        # Count log files
        logs_dir = Path(".nova/logs")
        if logs_dir.exists():
            log_count = len(list(logs_dir.glob("*.log")))
        else:
            log_count = 0
        table.add_row("Log Files", str(log_count))

        console.print(table)

    def run_logs(self) -> None:
        """Run logs command."""
        console = Console()
        logs_dir = Path(".nova/logs")
        if not logs_dir.exists():
            console.print("[red]No logs directory found[/red]")
            return

        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            console.print("[yellow]No log files found[/yellow]")
            return

        # Get most recent log file
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        with latest_log.open() as f:
            # Get last 50 lines
            lines = f.readlines()[-50:]
            for line in lines:
                console.print(line.strip())

    def create_command(self) -> click.Command:
        """Create the Click command.

        Returns:
            click.Command: The Click command
        """

        @click.group(name="monitor")
        def monitor() -> None:
            """Monitor system health, stats, and logs."""

        @monitor.command()
        def health() -> None:
            """Check system health."""
            self.run(subcommand="health")

        @monitor.command()
        def stats() -> None:
            """Show system statistics."""
            self.run(subcommand="stats")

        @monitor.command()
        def logs() -> None:
            """Show recent log entries."""
            self.run(subcommand="logs")

        return monitor
