"""Search command."""

import logging
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class SearchCommand(NovaCommand):
    """Search command."""

    name = "search"
    help = "Search through vector embeddings"

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        query = kwargs["query"]
        vector_dir = kwargs.get("vector_dir", Path(".nova/vectors"))
        limit = kwargs.get("limit", 5)

        try:
            # Initialize vector store
            vector_store = VectorStore(vector_dir)

            # Search for similar documents
            results = vector_store.search(query, limit=limit)

            # Display results
            if not results:
                logger.info("No results found")
                return

            logger.info("Found %d results:", len(results))
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                score = 1.0 - result.get(
                    "distance", 0.0
                )  # Convert distance to similarity
                logger.info(
                    "\n%d. %s (%.2f%% match)\nTags: %s\nDate: %s\nContent: %s\n",
                    i,
                    metadata.get("title", "Untitled"),
                    score * 100,
                    metadata.get("tags", ""),
                    metadata.get("date", "Unknown"),
                    metadata.get("content", "")[:200] + "...",  # Show first 200 chars
                )

        except Exception as e:
            self.log_error(f"Failed to search: {e}")
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.argument("query", type=str)
        @click.option(
            "--vector-dir",
            type=click.Path(path_type=Path),
            default=Path(".nova/vectors"),
            help="Vector store directory",
        )
        @click.option(
            "--limit",
            type=int,
            default=5,
            help="Maximum number of results to return",
        )
        def command(query: str, vector_dir: Path, limit: int) -> None:
            self.run(query=query, vector_dir=vector_dir, limit=limit)

        return command
