"""Search command."""

import asyncio
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

    async def run_async(self, **kwargs: Any) -> None:
        """Run the command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        query = kwargs["query"]
        vector_dir = kwargs.get("vector_dir", Path(".nova/vectors"))
        limit = kwargs.get("limit", 5)

        try:
            # Initialize vector store
            vector_store = VectorStore(vector_dir)

            # Search for similar documents asynchronously
            results = await asyncio.to_thread(vector_store.search, query, limit=limit)

            # Display results
            if not results:
                print("No results found")
                return

            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                score = min(100.0, result["score"])  # Cap at 100%
                text = result["text"]

                print(
                    f"\n{i}. Score: {score:.2f}%\n"
                    f"Heading: {metadata.get('heading_text', 'No heading')}\n"
                    f"Tags: {metadata.get('tags', '[]')}\n"
                    f"Content: {text[:200] + '...' if len(text) > 200 else text}\n"
                )

        except Exception as e:
            self.log_error(f"Failed to search: {e}")
            raise click.Abort()

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        asyncio.run(self.run_async(**kwargs))

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
