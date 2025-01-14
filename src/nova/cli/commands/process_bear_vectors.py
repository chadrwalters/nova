"""Process Bear vectors command."""

import logging
from pathlib import Path
from typing import Any

import click
import numpy as np
from numpy.typing import NDArray

from nova.bear_parser.parser import BearParser
from nova.cli.utils.command import NovaCommand
from nova.vector_store.embedding import EmbeddingEngine
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class ProcessBearVectorsCommand(NovaCommand):
    """Process Bear vectors command."""

    name = "process-bear-vectors"
    help = "Process Bear notes into vector embeddings"

    def process_directory(
        self, directory: Path, embedding_engine: EmbeddingEngine
    ) -> tuple[list[NDArray[np.float32]], list[dict[str, str | int | float | bool]]]:
        """Process a directory of notes recursively.

        Args:
            directory: Directory to process
            embedding_engine: Embedding engine instance

        Returns:
            Tuple of (embeddings, metadatas)
        """
        embeddings: list[NDArray[np.float32]] = []
        metadatas: list[dict[str, str | int | float | bool]] = []

        # Process all notes using BearParser
        parser = BearParser(directory)
        notes = parser.process_notes(None)  # Don't write to output dir

        for note in notes:
            try:
                if not note.content:
                    self.log_warning(f"No content in note {note.title}")
                    continue

                # Create embedding for the note content
                embedding = embedding_engine.embed_text(note.content)
                embeddings.append(embedding.vector)

                # Create metadata for the note
                metadata: dict[str, str | int | float | bool] = {
                    "id": note.title,
                    "title": note.title,
                    "date": note.date.isoformat(),
                    "tags": ",".join(note.tags),
                    "content": note.content,
                }
                metadatas.append(metadata)

            except Exception as e:
                self.log_error(f"Failed to process note {note.title}: {e}")
                continue

        return embeddings, metadatas

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs["output_dir"]

        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize embedding engine and vector store
            embedding_engine = EmbeddingEngine()
            vector_store = VectorStore(output_dir)

            # Process notes and create embeddings
            embeddings, metadatas = self.process_directory(input_dir, embedding_engine)

            # Add embeddings to vector store
            vector_store.add_embeddings(embeddings, metadatas)

            self.log_success(
                f"Processed {len(embeddings)} notes into vector embeddings"
            )

        except Exception as e:
            self.log_error(f"Failed to process vectors: {e}")
            raise click.ClickException(str(e)) from e

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
        @click.argument("output_dir", type=click.Path(path_type=Path))
        def command(input_dir: Path, output_dir: Path) -> None:
            self.run(input_dir=input_dir, output_dir=output_dir)

        return command
