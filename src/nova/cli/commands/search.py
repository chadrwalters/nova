"""Search command."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, List
import json

import click

from nova.cli.utils.command import NovaCommand
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class SearchCommand(NovaCommand):
    """Search command."""

    name = "search"
    help = "Search through vector embeddings"

    def __init__(self) -> None:
        """Initialize command."""
        super().__init__()
        self._vector_store: Optional[VectorStore] = None

    async def run_async(self, **kwargs: Any) -> None:
        """Run the command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        query = kwargs["query"]
        vector_dir = kwargs.get("vector_dir", Path(".nova/vectors"))
        limit = kwargs.get("limit", 5)

        try:
            # Use injected vector store or create new one
            vector_store = self._vector_store or VectorStore(base_path=str(vector_dir))

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

                # Parse tags from metadata
                tags: List[str] = []
                if "tags" in metadata:
                    tags_value = metadata["tags"]
                    if isinstance(tags_value, str):
                        try:
                            tags = json.loads(tags_value)
                        except json.JSONDecodeError:
                            tags = [t.strip() for t in tags_value.split(",") if t.strip()]
                    elif isinstance(tags_value, list):
                        tags = tags_value
                tags_str = ", ".join(tags) if tags else "No tags"

                print(
                    f"\n{i}. Score: {score:.2f}% # raw_score: {result['score']}\n"
                    f"Heading: {metadata.get('heading_text', 'No heading')}\n"
                    f"Tags: {tags_str}\n"
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
        def search(query: str, vector_dir: Path, limit: int) -> None:
            """Search through vector embeddings.

            Args:
                query: The search query
                vector_dir: Vector store directory
                limit: Maximum number of results to return
            """
            self.run(query=query, vector_dir=vector_dir, limit=limit)

        return search
