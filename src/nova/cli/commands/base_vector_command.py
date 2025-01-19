"""Base vector processing command."""

import logging
import time
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
        logger.info("Initializing BaseVectorCommand")
        self.vector_store = vector_store
        logger.info(f"Vector store initialized: {vector_store is not None}")
        self.monitor = monitor or SessionMonitor(nova_dir=Path(".nova"))
        logger.info(f"Monitor initialized: {self.monitor}")
        self.chunking_engine = ChunkingEngine()
        logger.info("Chunking engine initialized")

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
        logger.info(f"Running sync with input_dir={input_dir}, output_dir={output_dir}")

        if not input_dir:
            raise click.UsageError("Input directory not specified")

        input_path = Path(input_dir)
        if not input_path.exists():
            raise click.UsageError(f"Input directory not found: {input_path}")

        output_path = Path(output_dir) if output_dir else None
        logger.info(f"Using output path: {output_path}")

        # Initialize vector store if not provided
        if not self.vector_store and output_path:
            logger.info(f"Creating new vector store at {output_path}")
            self.vector_store = VectorStore(base_path=str(output_path))
            logger.info(f"Vector store created: {self.vector_store}")

        # Process vectors
        try:
            logger.info(f"Processing directory: {input_path}")
            chunks = self._process_directory(input_path)
            logger.info(f"Directory processed, got {len(chunks)} chunks")

            if not chunks:
                logger.warning(f"No chunks were created from {input_path}")
                click.echo(f"WARNING: No chunks were created from {input_path}", err=True)
                return

            # Add chunks to vector store
            total_chunks = len(chunks)
            logger.info(f"Starting to add {total_chunks} chunks to vector store")
            self.monitor.track_rebuild_progress(total_chunks)
            start_time = time.time()

            for i, chunk in enumerate(chunks, 1):
                try:
                    if self.vector_store:
                        # Generate a unique ID for each chunk
                        chunk.chunk_id = str(uuid.uuid4())
                        logger.info(f"Processing chunk {i}/{total_chunks} with ID {chunk.chunk_id}")
                        logger.debug(f"Chunk content length: {len(chunk.text)}")
                        logger.debug(f"Chunk metadata: {chunk.to_metadata()}")

                        # Use chunk's built-in metadata method
                        self.vector_store.add_chunk(chunk)
                        logger.info(f"Successfully added chunk {i} to vector store")
                    else:
                        logger.warning("No vector store available to add chunks")

                    processing_time = time.time() - start_time
                    self.monitor.update_rebuild_progress(
                        chunks_processed=i, processing_time=processing_time
                    )
                    logger.debug(f"Chunk {i} processed in {processing_time:.2f}s")

                except Exception as e:
                    error_msg = f"Error adding chunk {i} to vector store: {e!s}"
                    logger.error(error_msg, exc_info=True)
                    self.monitor.record_rebuild_error(error_msg)
                    if hasattr(chunk, "source"):
                        logger.error(f"Error occurred while processing {chunk.source}")

            # Complete rebuild
            logger.info("Completing rebuild process")
            self.monitor.complete_rebuild()
            total_time = time.time() - start_time
            logger.info(f"Rebuild completed in {total_time:.2f}s")

        except Exception as e:
            error_msg = f"Failed to process vectors: {e!s}"
            logger.error(error_msg, exc_info=True)
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
