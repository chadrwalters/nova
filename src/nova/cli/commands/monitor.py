"""Monitor command for checking system health and stats."""
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import aiofiles
import aiofiles.os
import click
from rich.console import Console
from rich.table import Table

from ...vector_store.store import VectorStore
from ...vector_store.types import VectorStoreStats
from ..utils.command import NovaCommand
import os

class MonitorCommand(NovaCommand):
    """Monitor command for checking system health and stats."""

    name = "monitor"

    def create_command(self) -> click.Command:
        """Create the monitor command.

        Returns:
            click.Command: The monitor command
        """
        @click.command(name=self.name)
        @click.argument("subcommand", type=click.Choice(["health", "stats", "logs"]), default="health")
        def monitor(subcommand: str) -> None:
            """Monitor system health and stats.

            Args:
                subcommand: The subcommand to run (health, stats, logs)
            """
            asyncio.run(self.run_async(subcommand=subcommand))

        return monitor

    async def run_async(self, subcommand: str) -> None:
        """Run the command asynchronously.

        Args:
            subcommand: The subcommand to run (health, stats, logs)
        """
        if subcommand == "health":
            await self.run_health()
        elif subcommand == "stats":
            await self.run_stats()
        elif subcommand == "logs":
            await self.run_logs()
        else:
            raise ValueError(f"Unknown subcommand: {subcommand}")

    async def run_health(self) -> None:
        """Run health check."""
        console = Console()

        # Check vector store
        store = VectorStore(Path(".nova/vectors"))
        if store._store_dir.exists():
            console.print("[green]Vector store exists[/green]")
        else:
            console.print("[red]Vector store does not exist[/red]")

        # Check processing directory
        if Path(".nova/processing").exists():
            console.print("[green]Processing directory exists[/green]")
        else:
            console.print("[red]Processing directory does not exist[/red]")

        # Check logs directory
        if Path(".nova/logs").exists():
            console.print("[green]Logs directory exists[/green]")
        else:
            console.print("[red]Logs directory does not exist[/red]")

    async def run_stats(self) -> None:
        """Run stats command."""
        store = VectorStore(Path(".nova/vectors"))
        stats = await store.get_stats()

        console = Console()

        table = Table(title="Vector Store Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Collection", stats.collection_name)
        table.add_row("Embeddings", str(stats.num_embeddings))

        console.print(table)

        # Check processing directory
        processing_dir = Path(".nova/processing")
        if processing_dir.exists():
            files = [f for f in os.scandir(processing_dir) if f.is_file()]
            total_size = sum(f.stat().st_size for f in files)

            table = Table(title="Processing Directory Stats")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Files", str(len(files)))
            table.add_row("Total Size", f"{total_size / 1024:.2f} KB")
            console.print(table)
        else:
            console.print("[yellow]Processing directory does not exist[/yellow]")

        # Check logs directory
        logs_dir = Path(".nova/logs")
        if logs_dir.exists():
            files = [f for f in os.scandir(logs_dir) if f.is_file()]
            total_size = sum(f.stat().st_size for f in files)

            table = Table(title="Logs Directory Stats")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Files", str(len(files)))
            table.add_row("Total Size", f"{total_size / 1024:.2f} KB")
            console.print(table)
        else:
            console.print("[yellow]Logs directory does not exist[/yellow]")

    async def run_logs(self) -> None:
        """Run logs command."""
        log_dir = Path(".nova/logs")
        if not log_dir.exists():
            print("No log directory found.")
            return

        console = Console()
        table = Table(title="Recent Logs")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="magenta")
        table.add_column("Modified", style="green")

        files = sorted(
            [f for f in os.scandir(log_dir) if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:5]  # Show 5 most recent logs

        for f in files:
            stat = f.stat()
            table.add_row(
                f.name,
                f"{stat.st_size / 1024:.2f} KB",
                f"{stat.st_mtime}"
            )

        console.print(table)
