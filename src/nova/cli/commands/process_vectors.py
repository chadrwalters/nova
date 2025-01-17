"""Process vectors command."""

import json
import logging
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand
from nova.vector_store.chunking import Chunk, ChunkingEngine
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class ProcessVectorsCommand(NovaCommand):
    """Process vectors command."""

    name = "process-vectors"

    def __init__(self, vector_store: VectorStore | None = None):
        """Initialize the command.

        Args:
            vector_store: Optional VectorStore instance. If not provided, one will be created.
        """
        super().__init__()
        self.vector_store = vector_store
        self.chunking_engine = ChunkingEngine()

    def _process_text(self, text: str) -> list[Chunk]:
        """Process text input into chunks."""
        if not text:
            return []
        return self.chunking_engine.chunk_document(text)

    def _process_directory(self, directory: Path) -> list[Chunk]:
        """Process all markdown files in a directory."""
        chunks = []
        if directory.exists() and directory.is_dir():
            for file_path in directory.rglob("*.md"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                    file_chunks = self.chunking_engine.chunk_document(content, source=file_path)
                    chunks.extend(file_chunks)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e!s}")
        return chunks

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
                text: Input text or directory path
                output_dir: Output directory for vector store
        """
        text = kwargs["text"]
        output_dir = kwargs["output_dir"]
        output_path = Path(output_dir)

        try:
            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Initialize vector store if not provided
            if self.vector_store is None:
                self.vector_store = VectorStore(str(output_path))

            # Handle empty text
            if not text:
                logger.info("Empty text provided, no chunks to store")
                return

            # Process input
            input_path = Path(text)
            chunks = (
                self._process_directory(input_path)
                if input_path.exists() and input_path.is_dir()
                else self._process_text(text)
            )

            # Store chunks if any were created
            if chunks:
                for chunk in chunks:
                    metadata = {
                        "source": str(chunk.source) if chunk.source else "",
                        "heading_text": chunk.heading_text or "",
                        "heading_level": chunk.heading_level or 0,
                        "tags": json.dumps(chunk.tags or []),
                        "attachments": json.dumps(chunk.attachments or []),
                    }
                    self.vector_store.add_chunk(chunk, metadata)
                logger.info(f"Stored {len(chunks)} chunks in vector store")
            else:
                logger.info("No chunks to store")

        except Exception as e:
            logger.error(f"Failed to process vectors: {e!s}")
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the Click command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name="process-vectors")
        @click.option("--text", required=True, help="Input text or directory path")
        @click.option("--output-dir", required=True, help="Output directory for vector store")
        def process_vectors(text: str, output_dir: str) -> None:
            """Process text or markdown files into vector embeddings."""
            self.run(text=text, output_dir=output_dir)

        return process_vectors
