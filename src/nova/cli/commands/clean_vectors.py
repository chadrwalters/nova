"""Clean vectors command."""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import chromadb
import click
from chromadb.config import Settings

from nova.cli.utils.command import NovaCommand
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class CleanVectorsCommand(NovaCommand):
    """Clean vectors command for nova CLI."""

    name = "clean-vectors"
    help = "Clean the vector store"

    async def run_async(self, **kwargs: Any) -> None:
        """Run the clean-vectors command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        force = kwargs.get("force", False)
        vector_dir = Path(".nova/vectors")

        if not await aiofiles.os.path.exists(str(vector_dir)):
            logger.info("Vector store directory does not exist")
            return

        if not force:
            logger.warning("Use --force to actually delete the vector store")
            return

        try:
            # Try to delete collection first if it exists
            try:
                client = chromadb.PersistentClient(
                    path=str(vector_dir / "chroma"),
                    settings=Settings(
                        persist_directory=str(vector_dir / "chroma"), is_persistent=True
                    ),
                )
                try:
                    collection = client.get_collection(name=VectorStore.COLLECTION_NAME)
                    collection.delete()
                    logger.info(f"Deleted collection: {VectorStore.COLLECTION_NAME}")
                except ValueError:
                    # Collection doesn't exist, that's fine
                    logger.info(f"Collection {VectorStore.COLLECTION_NAME} does not exist")
                except Exception as e:
                    # Log other collection errors but continue
                    logger.warning(f"Error deleting collection: {e}")
            except Exception as e:
                # Log ChromaDB errors but continue
                logger.warning(f"Error accessing ChromaDB: {e}")

            # Run rmtree in a thread to avoid blocking
            await asyncio.to_thread(shutil.rmtree, vector_dir)
            logger.info("Vector store deleted successfully")

            # Reset VectorStore singleton
            VectorStore._instance = None
            VectorStore._initialized = False

        except Exception as e:
            msg = f"Failed to delete vector store: {e!s}"
            logger.error(msg)
            raise click.Abort(msg) from e

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
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

            This command deletes the vector store directory and all its
            contents. Use with caution as this operation cannot be
            undone.
            """
            self.run(force=force)

        return clean_vectors
