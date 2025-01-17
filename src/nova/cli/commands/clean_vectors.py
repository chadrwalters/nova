"""Clean vectors command."""

import logging
import shutil
from pathlib import Path
from typing import Any

import click
import chromadb

from nova.cli.utils.command import NovaCommand
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class CleanVectorsCommand(NovaCommand):
    """Clean vectors command for nova CLI."""

    name = "clean-vectors"
    help = "Clean the vector store"

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
                force: Whether to force deletion
        """
        force = kwargs.get("force", False)
        if not force:
            logger.warning("Use --force to actually delete the vector store")
            return

        try:
            # Clean up ChromaDB collection
            try:
                vector_dir = Path(".nova/vectors")
                client = chromadb.PersistentClient(path=str(vector_dir))
                client.delete_collection(VectorStore.COLLECTION_NAME)
                logger.info("✨ Reset ChromaDB database")
            except Exception as e:
                logger.info(f"No ChromaDB collection to clean up: {e}")

            # Delete vector store directory
            vector_dir = Path(".nova/vectors")
            if vector_dir.exists():
                shutil.rmtree(vector_dir)
                logger.info("🗑️  Vector store deleted successfully")
            else:
                logger.info("Vector store directory does not exist")

        except Exception as e:
            logger.error(f"Failed to clean vector store: {e}")
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the Click command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--force",
            is_flag=True,
            help="Force deletion of vector store",
        )
        def clean_vectors(force: bool) -> None:
            """Clean the vector store."""
            self.run(force=force)

        return clean_vectors
