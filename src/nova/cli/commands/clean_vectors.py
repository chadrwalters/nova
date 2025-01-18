"""Clean vectors command."""

import logging
import shutil
from typing import Any

import chromadb
import click

from nova.cli.utils.command import NovaCommand
from nova.config import load_config
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class CleanVectorsCommand(NovaCommand):
    """Clean vectors command for nova CLI."""

    name = "clean-vectors"
    help = "Clean the vector store"

    def __init__(self) -> None:
        """Initialize clean vectors command."""
        super().__init__()
        self.config = load_config()

    async def run_async(self, **kwargs: Any) -> None:
        """Run the clean-vectors command asynchronously.

        Args:
            **kwargs: Command arguments
                force: Whether to force deletion
        """
        force = kwargs.get("force", False)
        vector_dir = self.config.paths.vector_store_dir

        if not vector_dir.exists():
            self.log_info("Vector store directory does not exist")
            return

        if not force:
            self.log_warning("Use --force to actually delete the vector store")
            return

        try:
            # Clean up ChromaDB collection
            try:
                client = chromadb.PersistentClient(path=str(vector_dir))
                client.delete_collection(VectorStore.COLLECTION_NAME)
                self.log_info("Vector store collection deleted")
            except Exception as e:
                self.log_info(f"No ChromaDB collection to clean up: {e}")

            # Delete vector store directory
            shutil.rmtree(vector_dir)
            self.log_info("Vector store deleted successfully")

        except PermissionError as e:
            msg = f"Failed to delete vector store: {e}"
            self.log_error(msg)
            raise click.Abort(msg)
        except Exception as e:
            msg = f"Failed to delete vector store: {e}"
            self.log_error(msg)
            raise click.Abort(msg)

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        import asyncio

        asyncio.run(self.run_async(**kwargs))

    def create_command(self) -> click.Command:
        """Create the clean-vectors command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--force",
            is_flag=True,
            help="Force deletion without confirmation",
        )
        def clean_vectors(force: bool) -> None:
            """Clean the vector store.

            This command deletes the vector store and all its contents.
            Use with caution as this operation cannot be undone.
            """
            self.run(force=force)

        return clean_vectors
