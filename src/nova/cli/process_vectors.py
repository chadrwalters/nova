#!/usr/bin/env python3
"""CLI module to process text into vectors using the Nova vector store."""
import logging
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand
from nova.vector_store.chunking import ChunkingEngine
from nova.vector_store.embedding import EmbeddingEngine
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class ProcessVectorsCommand(NovaCommand):
    """Command for processing vectors."""

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        text = kwargs["text"]
        output_dir = kwargs["output_dir"]

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize engines
        chunking_engine = ChunkingEngine()
        embedding_engine = EmbeddingEngine()
        vector_store = VectorStore(output_path)

        try:
            # Create chunks
            chunks = chunking_engine.chunk_document(text)
            logger.info(f"Created {len(chunks)} chunks")

            # Create embeddings
            embeddings = []
            metadata_dicts: list[dict[str, Any]] = []
            for chunk in chunks:
                embedding = embedding_engine.embed_text(chunk.text)
                embeddings.append(embedding.vector)
                metadata_dicts.append(
                    {
                        "text": chunk.text,
                        "source": str(chunk.source) if chunk.source else "",
                        "heading_context": chunk.heading_context,
                        "tags": chunk.tags,
                    }
                )

            # Store embeddings
            vector_store.add_embeddings(embeddings, metadata_dicts)
            logger.info("Stored embeddings in vector store")

        except Exception as e:
            logger.error(f"Failed to process vectors: {e!s}")
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the command.

        Returns:
            Click command object
        """

        @click.command(name="process-vectors")
        @click.option("--text", required=True, help="Input text to process")
        @click.option("--output-dir", required=True, help="Output directory for vector store")
        def command(text: str, output_dir: str) -> None:
            """Process text into vector embeddings."""
            self.run(text=text, output_dir=output_dir)

        return command


if __name__ == "__main__":
    command = ProcessVectorsCommand()
    command.create_command()()
