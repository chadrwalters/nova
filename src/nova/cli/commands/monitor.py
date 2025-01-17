"""Monitor command for checking system health and stats."""

import logging
from pathlib import Path

import click
from rich.console import Console

from nova.cli.utils.command import NovaCommand
from nova.monitoring.logs import LogManager
from nova.vector_store.stats import VectorStoreStats
from nova.vector_store.store import VectorStore

console = Console()
logger = logging.getLogger(__name__)


class MonitorCommand(NovaCommand):
    """Command for monitoring system health and stats."""

    name = "monitor"
    help = "Monitor system health and stats"

    def __init__(self, vector_dir: str = ".nova/vectors"):
        """Initialize the command."""
        super().__init__()
        self.vector_dir = Path(vector_dir)
        self.stats_file = self.vector_dir / "stats.json"
        self.vector_stats = VectorStoreStats()
        self.log_manager = LogManager()

        # Get the singleton VectorStore instance
        self.vector_store = VectorStore(vector_dir=str(self.vector_dir))

    def create_command(self):
        """Create the Click command."""

        @click.command(name=self.name, help=self.help)
        @click.argument("subcommand", type=click.Choice(["health", "stats", "logs"]))
        def monitor(subcommand):
            """Monitor system health and stats."""
            self._run_sync(subcommand=subcommand)

        return monitor

    def _run_sync(self, subcommand: str):
        """Run the command synchronously."""
        try:
            if subcommand == "health":
                self._check_health()
            elif subcommand == "stats":
                self._show_stats()
            elif subcommand == "logs":
                self._show_logs()
            else:
                raise ValueError(f"Invalid subcommand: {subcommand}")
        except Exception as e:
            logger.error(f"Error running command: {e}")
            raise

    def _check_health(self):
        """Check system health."""
        try:
            # Check vector store directory
            if not self.vector_dir.exists():
                console.print("❌ Vector store directory does not exist", style="red")
            else:
                console.print("✅ Vector store directory exists", style="green")

            # Check ChromaDB directory
            chroma_dir = self.vector_dir / "chroma"
            if not chroma_dir.exists():
                console.print("❌ ChromaDB directory does not exist", style="red")
            else:
                console.print("✅ ChromaDB directory exists", style="green")

            # Check cache directory
            cache_dir = Path(".nova/cache")
            if not cache_dir.exists():
                console.print("❌ Cache directory does not exist", style="red")
            else:
                console.print("✅ Cache directory exists", style="green")

            # Check logs directory
            logs_dir = Path(".nova/logs")
            if not logs_dir.exists():
                console.print("❌ Logs directory does not exist", style="red")
            else:
                console.print("✅ Logs directory exists", style="green")

            # Verify ChromaDB collection
            try:
                collection = self.vector_store.collection
                if collection is not None:
                    console.print("✅ ChromaDB collection is accessible", style="green")
                else:
                    console.print("❌ ChromaDB collection is not accessible", style="red")
            except Exception as e:
                console.print(f"❌ ChromaDB collection error: {e}", style="red")

        except Exception as e:
            logger.error(f"Error checking health: {e}")
            raise

    def _show_stats(self):
        """Show system statistics."""
        try:
            # Get collection stats
            collection = self.vector_store.collection
            total_docs = 0
            if collection is not None:
                result = collection.get()
                total_docs = len(result["ids"]) if result and "ids" in result else 0

            # Get stats from vector store
            stats = self.vector_store.stats
            stats_dict = stats.get_stats() if stats else {}

            console.print("\nVector Store Statistics:", style="bold cyan")
            console.print(f"Documents in collection: {total_docs}")
            console.print(f"Total documents processed: {stats_dict.get('total_documents', 0)}")
            console.print(f"Total chunks: {stats_dict.get('total_chunks', 0)}")
            console.print(f"Total embeddings: {stats_dict.get('total_embeddings', 0)}")
            console.print(f"Total searches: {stats_dict.get('total_searches', 0)}")
            console.print(f"Cache hits: {stats_dict.get('cache_hits', 0)}")
            console.print(f"Cache misses: {stats_dict.get('cache_misses', 0)}")
            console.print(f"Last update: {stats_dict.get('last_update', 'Never')}")

            # Get log statistics
            log_stats = self.log_manager.get_stats()
            console.print("\nLog Statistics:", style="bold cyan")
            console.print(f"Total log files: {log_stats['total_files']}")
            console.print(f"Total entries: {log_stats['total_entries']}")
            console.print(f"Error entries: {log_stats['error_entries']}")
            console.print(f"Warning entries: {log_stats['warning_entries']}")
            console.print(f"Info entries: {log_stats['info_entries']}")

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            raise

    def _show_logs(self):
        """Show recent logs."""
        try:
            console.print("\nRecent Log Entries:", style="bold cyan")
            logs = self.log_manager.tail_logs(100)
            for log in logs:
                timestamp = log["timestamp"]
                level = log["level"]
                message = log["message"]
                style = "red" if level == "ERROR" else "yellow" if level == "WARNING" else "green"
                console.print(f"[{timestamp}] [{level}] {message}", style=style)
        except Exception as e:
            logger.error(f"Error showing logs: {e}")
            raise
