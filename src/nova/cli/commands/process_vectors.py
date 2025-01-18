"""Process vectors command."""

import logging
from pathlib import Path
from typing import List, Optional

import click

from nova.cli.commands.base_vector_command import BaseVectorCommand
from nova.vector_store.chunking import Chunk
from nova.bear_parser.processing import BearNoteProcessing

logger = logging.getLogger(__name__)

class ProcessVectorsCommand(BaseVectorCommand):
    """Process vectors command."""

    name = "process-vectors"
    help = "Process text files or Bear notes into vector chunks"

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
        @click.option(
            "--bear-notes",
            is_flag=True,
            help="Process input directory as Bear notes",
            default=False,
        )
        def command(input_dir: str, output_dir: Optional[str] = None, bear_notes: bool = False) -> None:
            """Process text files into vector chunks.

            Args:
                input_dir: Input directory containing text files
                output_dir: Optional output directory for vector store
                bear_notes: Whether to process input directory as Bear notes
            """
            self.run(input_dir=input_dir, output_dir=output_dir, bear_notes=bear_notes)

        return command

    def _process_directory(self, directory: Path, bear_notes: bool = False) -> List[Chunk]:
        """Process files in a directory.

        Args:
            directory: Directory containing files to process
            bear_notes: Whether to process as Bear notes

        Returns:
            List of chunks created from files

        Raises:
            Exception: If there is an error processing any file
        """
        if not directory.exists():
            raise click.UsageError(f"Directory not found: {directory}")

        if bear_notes:
            return self._process_bear_notes(directory)
        else:
            return self._process_markdown_files(directory)

    def _process_bear_notes(self, directory: Path) -> List[Chunk]:
        """Process Bear notes in a directory.

        Args:
            directory: Directory containing Bear notes

        Returns:
            List of chunks created from Bear notes
        """
        # Use BearNoteProcessing to get documents
        processor = BearNoteProcessing(input_dir=directory)
        documents = processor.process_bear_notes()

        # Process each document into chunks
        chunks: List[Chunk] = []
        for doc in documents:
            try:
                # Create chunks using chunking engine
                file_chunks = self.chunking_engine.chunk_document(
                    text=doc.content,
                    source=Path(doc.origin) if doc.origin else None
                )
                chunks.extend(file_chunks)
            except Exception as e:
                error_msg = f"Error processing document {doc.name}: {e!s}"
                logger.error(error_msg)
                self.monitor.record_rebuild_error(error_msg)
                continue

        return chunks

    def _process_markdown_files(self, directory: Path) -> List[Chunk]:
        """Process markdown files in a directory.

        Args:
            directory: Directory containing markdown files

        Returns:
            List of chunks created from markdown files
        """
        chunks: List[Chunk] = []
        for file_path in directory.glob("**/*.md"):
            try:
                # Read the file content
                try:
                    text = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # If UTF-8 fails, try Latin-1
                    try:
                        text = file_path.read_text(encoding="latin-1")
                        logger.warning(f"File {file_path} contains non-UTF-8 characters")
                    except Exception as e:
                        error_msg = f"Error reading file {file_path}: {e!s}"
                        logger.error(error_msg)
                        self.monitor.record_rebuild_error(error_msg)
                        continue
                except Exception as e:
                    error_msg = f"Error reading file {file_path}: {e!s}"
                    logger.error(error_msg)
                    self.monitor.record_rebuild_error(error_msg)
                    continue

                # Check for null bytes
                if "\x00" in text:
                    error_msg = f"File {file_path} contains null bytes"
                    logger.error(error_msg)
                    self.monitor.record_rebuild_error(error_msg)
                    continue

                # Process the file content
                file_chunks = self.chunking_engine.chunk_document(text, source=file_path)
                if not file_chunks:
                    error_msg = f"No chunks created from file {file_path}"
                    logger.warning(error_msg)
                    self.monitor.record_rebuild_error(error_msg)
                chunks.extend(file_chunks)

            except Exception as e:
                error_msg = f"Error processing file {file_path}: {e!s}"
                logger.error(error_msg)
                self.monitor.record_rebuild_error(error_msg)

        return chunks
