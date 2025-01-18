"""Base vector processing command."""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand
from nova.monitoring.session import SessionMonitor
from nova.vector_store.chunking import Chunk, ChunkingEngine
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class BaseVectorCommand(NovaCommand):
    """Base class for vector processing commands."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        monitor: SessionMonitor | None = None,
    ) -> None:
        """Initialize the command.

        Args:
            vector_store: Optional vector store instance
            monitor: Optional session monitor instance
        """
        super().__init__()
        self.vector_store = vector_store
        self.monitor = monitor or SessionMonitor(nova_dir=Path(".nova"))
        self.chunking_engine = ChunkingEngine()

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--input-dir",
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
            help="Input directory containing text files",
            required=True,
        )
        @click.option(
            "--output-dir",
            type=click.Path(file_okay=False, dir_okay=True),
            help="Output directory for vector store",
            required=False,
        )
        def command(input_dir: str, output_dir: str | None = None) -> None:
            """Process text files into vector chunks.

            Args:
                input_dir: Input directory path
                output_dir: Output directory path (optional)
            """
            kwargs = {"input_dir": input_dir}
            if output_dir:
                kwargs["output_dir"] = output_dir
            self.run(**kwargs)

        return command

    def run(self, **kwargs: Any) -> None:
        """Run the command with the given arguments.

        Args:
            **kwargs: Command arguments
                input_dir: Input directory path
                output_dir: Output directory path (optional)
        """
        super().run(**kwargs)

    def _run_sync(self, **kwargs: Any) -> None:
        """Run the command synchronously.

        Args:
            **kwargs: Command arguments
                input_dir: Input directory path
                output_dir: Output directory path (optional)
        """
        input_dir = kwargs.get("input_dir")
        output_dir = kwargs.get("output_dir")

        if not input_dir:
            raise click.UsageError("Input directory not specified")

        input_path = Path(input_dir)
        if not input_path.exists():
            raise click.UsageError(f"Input directory not found: {input_path}")

        output_path = Path(output_dir) if output_dir else None

        # Initialize vector store if not provided
        if not self.vector_store and output_path:
            self.vector_store = VectorStore(base_path=str(output_path))

        # Process vectors
        try:
            chunks = self._process_directory(input_path)
            if not chunks:
                logger.warning(f"No chunks were created from {input_path}")
                click.echo(f"WARNING: No chunks were created from {input_path}", err=True)
                return

            # Add chunks to vector store
            total_chunks = len(chunks)
            self.monitor.track_rebuild_progress(total_chunks)
            for i, chunk in enumerate(chunks, 1):
                try:
                    if self.vector_store:
                        # Generate a unique ID for each chunk
                        chunk.chunk_id = str(uuid.uuid4())
                        metadata = {
                            "source": str(chunk.source) if chunk.source else "",
                            "heading_text": chunk.heading_text,
                            "heading_level": str(chunk.heading_level),
                            "tags": json.dumps(chunk.tags),
                            "attachments": json.dumps(chunk.attachments),
                        }
                        self.vector_store.add_chunk(chunk, metadata)
                    self.monitor.update_rebuild_progress(chunks_processed=i, processing_time=0.0)
                except Exception as e:
                    error_msg = f"Error adding chunk to vector store: {e!s}"
                    logger.error(error_msg)
                    self.monitor.record_rebuild_error(error_msg)
                    if hasattr(chunk, "source"):
                        logger.error(f"Error occurred while processing {chunk.source}")

            # Complete rebuild
            self.monitor.complete_rebuild()
        except Exception as e:
            error_msg = f"Failed to process vectors: {e!s}"
            logger.error(error_msg)
            self.monitor.record_rebuild_error(error_msg)
            raise click.UsageError(error_msg)

    def _process_directory(self, directory: Path) -> list[Chunk]:
        """Process all files in a directory.

        This method should be implemented by subclasses to handle specific file types.

        Args:
            directory: Directory containing files to process

        Returns:
            List of chunks created from files

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _process_directory")
