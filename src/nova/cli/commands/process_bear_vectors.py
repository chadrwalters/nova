"""Process Bear notes into vector embeddings."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from nova.bear_parser.parser import BearParser
from nova.cli.utils.command import NovaCommand
from nova.vector_store.chunking import Chunk, ChunkingEngine
from nova.vector_store.embedding import EmbeddingEngine
from nova.vector_store.stats import VectorStoreStats
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class ProcessBearVectorsCommand(NovaCommand):
    """Command to process Bear notes into vector embeddings."""

    name = "process-bear-vectors"
    help = "Process Bear notes into vector embeddings"

    def __init__(self) -> None:
        """Initialize command."""
        super().__init__()
        self.chunking_engine = ChunkingEngine()
        self.vector_stats = VectorStoreStats()
        # Date patterns in titles (e.g., "20240115 - Meeting Notes" or "2024-01-15 Meeting")
        self.date_patterns = [
            r"^(\d{8})\s*[-\s]",  # 20240115
            r"^(\d{4}-\d{2}-\d{2})\s",  # 2024-01-15
            r"^(\d{4}\d{2}\d{2})\s",  # 20240115
        ]

    def create_command(self) -> click.Command:
        """Create the command.

        Returns:
            The Click command for processing Bear notes.
        """

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--input-dir",
            required=True,
            help="Directory containing Bear notes",
        )
        @click.option(
            "--output-dir",
            default=".nova/vectors",
            help="Directory for vector store (default: .nova/vectors)",
        )
        def command(input_dir: str, output_dir: str) -> None:
            self.run(input_dir=input_dir, output_dir=output_dir)

        return command

    def _run_sync(self, **kwargs: Any) -> None:
        """Run the command synchronously.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs.get("output_dir", ".nova/vectors")
        self.process_bear_vectors(input_dir, output_dir)

    def process_bear_vectors(self, input_dir: str, output_dir: str) -> None:
        """Process Bear notes into vector embeddings.

        Args:
            input_dir: Directory containing Bear notes
            output_dir: Directory for vector store
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            self.log_error(f"Input directory does not exist: {input_dir}")
            return

        self.log_info(f"Processing Bear notes from {input_dir}")
        self.log_info(f"Vector store output to {output_dir}")

        # Initialize vector store
        try:
            vector_store = VectorStore(vector_dir=str(output_dir))
            embedding_engine = EmbeddingEngine()

            # Process files with progress bar
            with self.create_progress() as progress:
                task_id = progress.add_task("Processing Bear notes...", total=None, start=True)

                try:
                    chunks = self.process_directory(input_path, embedding_engine, progress, task_id)

                    # Store chunks in vector store
                    total_chunks = len(chunks)
                    self.log_info(f"Processing {total_chunks} chunks")

                    if total_chunks > 0:
                        store_task = progress.add_task("Storing vectors...", total=total_chunks)

                        for i, chunk in enumerate(chunks, 1):
                            try:
                                metadata = {
                                    "source": str(chunk.source) if chunk.source else "",
                                    "heading_text": chunk.heading_text,
                                    "heading_level": chunk.heading_level,
                                    "tags": json.dumps(chunk.tags),
                                    "attachments": json.dumps(
                                        [{"type": att["type"]} for att in chunk.attachments]
                                    ),
                                }
                                vector_store.add_chunk(chunk, metadata=metadata)
                                progress.update(
                                    store_task,
                                    advance=1,
                                    description=f"Stored {i}/{total_chunks} vectors",
                                )
                            except Exception as e:
                                self.log_error(f"Failed to add chunk to vector store: {e}")
                                continue

                        progress.update(store_task, description="Vectors stored")
                        self.log_success(
                            f"Successfully processed {total_chunks} chunks from {input_dir}"
                        )
                    else:
                        self.log_warning("No chunks were generated from the input directory")

                except Exception as e:
                    self.log_error(f"Error processing chunks: {e}")
                    raise

        except Exception as e:
            self.log_error(f"Error initializing vector store: {e}")
            raise

    def extract_date_from_title(self, title: str) -> datetime | None:
        """Extract date from document title if present.

        Args:
            title: Document title

        Returns:
            Extracted datetime or None
        """
        for pattern in self.date_patterns:
            match = re.match(pattern, title)
            if match:
                date_str = match.group(1)
                try:
                    # Handle different date formats
                    if "-" in date_str:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        return datetime.strptime(date_str, "%Y%m%d")
                except ValueError:
                    continue
        return None

    def process_directory(
        self,
        directory: Path,
        embedding_engine: EmbeddingEngine,
        progress: Progress | None = None,
        task_id: TaskID | None = None,
    ) -> list[Chunk]:
        """Process all Bear notes in a directory.

        Args:
            directory: Directory containing Bear notes
            embedding_engine: Engine for creating embeddings
            progress: Optional progress bar
            task_id: Optional task ID for progress

        Returns:
            List of processed chunks
        """
        chunks: list[Chunk] = []
        parser = BearParser(input_dir=directory)

        try:
            # Parse all notes in directory
            parser.parse_directory()
            notes = parser.process_notes()

            # Process each note
            for note in notes:
                if progress and task_id:
                    progress.update(task_id, description=f"Processing {note.name}")

                try:
                    # Create chunks using chunking engine
                    file_chunks = self.chunking_engine.chunk_document(
                        text=note.content, source=Path(note.origin) if note.origin else None
                    )
                    chunks.extend(file_chunks)

                except Exception as e:
                    self.log_error(f"Error processing note {note.name}: {e}")
                    continue

        except Exception as e:
            self.log_error(f"Error processing directory {directory}: {e}")

        return chunks

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
                input_dir: Input directory path
                output_dir: Output directory path (optional, defaults to .nova/vectors)
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs.get("output_dir", ".nova/vectors")

        # Validate paths
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        # Validate paths
        if not input_path.exists():
            self.log_error(f"Input directory does not exist: {input_path}")
            return

        if not input_path.is_dir():
            self.log_error(f"Input path is not a directory: {input_path}")
            return

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        embedding_engine = EmbeddingEngine()
        vector_store = VectorStore(str(output_path))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress:
                # Process notes
                task_id = progress.add_task("Processing notes...", total=None)
                chunks = self.process_directory(input_path, embedding_engine, progress, task_id)
                progress.update(task_id, description="Notes processed")

                # Add chunks to vector store
                if chunks:
                    store_task = progress.add_task("Adding to vector store...", total=len(chunks))
                    for chunk in chunks:
                        try:
                            metadata = {
                                "source": str(chunk.source) if chunk.source else "",
                                "heading_text": chunk.heading_text,
                                "heading_level": chunk.heading_level,
                                "tags": json.dumps(chunk.tags),
                                "attachments": json.dumps(
                                    [{"type": att["type"]} for att in chunk.attachments]
                                ),
                            }
                            vector_store.add_chunk(chunk, metadata=metadata)
                            progress.update(store_task, advance=1)
                        except Exception as e:
                            self.log_error(f"Failed to add chunk to vector store: {e}")
                            continue

                    progress.update(store_task, description="Vectors stored")
                    self.log_success(
                        f"Successfully processed {len(chunks)} chunks from {input_path}"
                    )
                else:
                    self.log_warning("No chunks were generated from the input directory")

        except Exception as e:
            self.log_error(f"Failed to process directory: {e}")
            raise


@click.command()
@click.option(
    "--input-dir",
    required=True,
    help="Directory containing Bear notes",
)
@click.option(
    "--output-dir",
    default=".nova/vectors",
    help="Directory for vector store (default: .nova/vectors)",
)
def process_bear_vectors(input_dir: str, output_dir: str) -> None:
    """Process Bear notes into vector embeddings.

    This command:
    1. Processes Bear notes from INPUT_DIR
    2. Splits notes into semantic chunks
    3. Creates vector embeddings
    4. Stores vectors with metadata in OUTPUT_DIR
    """
    command = ProcessBearVectorsCommand()
    command.run(input_dir, output_dir)
