"""Process Bear vectors command."""

import logging
from pathlib import Path
from typing import Any

import click
from nova.cli.utils.command import NovaCommand
from nova.ingestion.bear import process_note
from nova.vector_store.embedding import EmbeddingEngine
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class ProcessBearVectorsCommand(NovaCommand):
    """Process Bear vectors command."""

    name = "process-bear-vectors"

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments

        Raises:
            KeyError: If required arguments are missing
        """
        if not kwargs:
            raise KeyError("No arguments provided")

        input_dir = kwargs.get("input_dir")
        output_dir = kwargs.get("output_dir")

        if not input_dir or not output_dir:
            raise KeyError("Input and output directories are required")

        input_path = Path(input_dir)
        if not input_path.exists():
            raise KeyError(f"Input directory {input_dir} does not exist")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize engines
        embedding_engine = EmbeddingEngine()
        vector_store = VectorStore(store_dir=output_path)

        # Process notes
        note_files = list(input_path.glob("*.md"))
        if not note_files:
            logger.warning("No note files found in %s", input_dir)
            return

        # Process all notes and collect embeddings
        embeddings = []
        metadatas = []
        for note_file in note_files:
            try:
                # Process note
                note = process_note(note_file)
                if not note.content:
                    logger.warning("No content in note %s", note_file.name)
                    continue

                # Create embedding for the note content
                embedding = embedding_engine.embed_text(note.content)
                metadata: dict[str, str | int | float | bool] = {
                    "source": str(note_file),
                    "text": note.content,
                    "title": note.title,
                    "date": note.date.isoformat(),
                    "tags": ",".join(note.tags),
                }

                embeddings.append(embedding.vector)
                metadatas.append(metadata)
                logger.info("Processed note: %s", note_file.name)
            except Exception as e:
                logger.error("Failed to process note %s: %s", note_file.name, e)
                raise

        # Add all embeddings to vector store at once
        if embeddings:
            vector_store.add_embeddings(embeddings, metadatas)

    def create_command(self) -> click.Command:
        """Create the command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name="process-bear-vectors")
        @click.option(
            "--input-dir", required=True, help="Input directory containing Bear notes"
        )
        @click.option(
            "--output-dir", required=True, help="Output directory for vector store"
        )
        def process_bear_vectors(input_dir: str, output_dir: str) -> None:
            """Process Bear notes into vector embeddings.

            This command processes Bear notes from the input directory
            into vector embeddings and stores them in the output
            directory using a vector store.
            """
            try:
                self.run(input_dir=input_dir, output_dir=output_dir)
            except Exception as e:
                logger.error("Failed to process Bear vectors: %s", e)
                raise

        return process_bear_vectors
