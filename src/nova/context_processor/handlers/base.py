"""Base handler for file processing."""

# Standard library
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..models.document import DocumentMetadata
from ..utils.output_manager import OutputManager
from ..utils.path_utils import ensure_parent_dirs, get_safe_path


class ProcessingStatus:
    """Status of file processing."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNCHANGED = "unchanged"


class ProcessingResult:
    """Result of file processing."""

    def __init__(
        self,
        status: str,
        metadata: Optional[DocumentMetadata] = None,
        error: Optional[str] = None,
    ):
        """Initialize result.

        Args:
            status: Processing status
            metadata: Document metadata
            error: Error message if any
        """
        self.status = status
        self.metadata = metadata
        self.error = error


class BaseHandler(ABC):
    """Base class for file handlers."""

    name = "base"
    version = "0.1.0"
    file_types: List[str] = []

    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.

        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.markdown_writer = MarkdownWriter()
        self.output_manager = OutputManager(config)

    def supports_file(self, file_path: Path) -> bool:
        """Check if handler supports file type.

        Args:
            file_path: Path to file

        Returns:
            True if handler supports file type
        """
        return file_path.suffix.lstrip(".").lower() in self.file_types

    async def process(
        self, file_path: Path, metadata: DocumentMetadata
    ) -> ProcessingResult:
        """Process a file.

        Args:
            file_path: Path to file
            metadata: Document metadata

        Returns:
            Processing result
        """
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                return ProcessingResult(
                    status=ProcessingStatus.FAILED, error=f"File not found: {file_path}"
                )

            if not os.access(file_path, os.R_OK):
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error=f"Cannot access file: {file_path}",
                )

            # Get output path
            rel_path = self._get_relative_path(file_path)
            output_path = self._get_output_path(rel_path, "parse", ".md")

            # Process the file
            updated_metadata = await self.process_impl(file_path, output_path, metadata)

            if updated_metadata is None:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error=f"Failed to process file: {file_path}",
                )

            if updated_metadata.errors:
                # Get the first error message from the errors dictionary
                first_error = next(iter(updated_metadata.errors.values()))
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    metadata=updated_metadata,
                    error=str(first_error),
                )

            return ProcessingResult(
                status=ProcessingStatus.COMPLETED, metadata=updated_metadata
            )

        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED, metadata=metadata, error=error_msg
            )

    def _get_relative_path(self, file_path: Path) -> Path:
        """Get relative path from input directory.

        Args:
            file_path: Path to file

        Returns:
            Relative path from input directory
        """
        try:
            # Convert to absolute path if not already
            abs_path = file_path if file_path.is_absolute() else file_path.resolve()

            # Get relative path from input directory
            rel_path = abs_path.relative_to(self.config.input_dir)

            return rel_path
        except ValueError:
            # If not under input directory, try to find a parent directory that matches
            # Look for common parent directories like "Format Test" or "Format Test 3"
            parts = file_path.parts
            for i in range(len(parts) - 1, -1, -1):
                if "Format Test" in parts[i]:
                    return Path(*parts[i:])

            # If no match found, use just the filename
            return Path(file_path.name)

    def _get_output_path(self, file_path: Path, phase: str, suffix: str) -> Path:
        """Get output path for a file.

        Args:
            file_path: Path to file
            phase: Phase name
            suffix: File suffix

        Returns:
            Output path
        """
        # Get relative path from input directory
        rel_path = self._get_relative_path(file_path)

        # Get output path using output manager
        output_path = self.output_manager.get_output_path_for_phase(
            rel_path, phase, suffix
        )

        return output_path

    async def process_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a file implementation.

        Args:
            file_path: Path to file
            output_path: Path to output file
            metadata: Document metadata

        Returns:
            Updated document metadata
        """
        try:
            # Get relative path from input directory
            rel_path = self._get_relative_path(file_path)

            # Process file and update metadata
            metadata = await self.process_file_impl(file_path, output_path, metadata)
            if metadata:
                # Save metadata using relative path
                self._save_metadata(file_path, rel_path, metadata)

            return metadata

        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            if metadata:
                metadata.add_error(self.name, str(e))
                metadata.processed = False
            return None

    @abstractmethod
    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a file implementation.

        Args:
            file_path: Path to file
            output_path: Path to write output
            metadata: Document metadata

        Returns:
            Updated document metadata
        """
        raise NotImplementedError("Subclasses must implement process_file_impl")

    def _save_metadata(
        self, file_path: Path, relative_path: Path, metadata: DocumentMetadata
    ) -> None:
        """Save metadata for a file.

        Args:
            file_path: Path to file
            relative_path: Relative path from input directory
            metadata: Document metadata
        """
        # Get output path for metadata
        metadata_path = self.output_manager.get_output_path_for_phase(
            relative_path, "parse", ".metadata.json"
        )

        # Ensure parent directories exist
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        # Write metadata
        metadata.save(metadata_path)

    def _safe_write_file(self, file_path: Path, content: str) -> bool:
        """Write content to file safely.

        Args:
            file_path: Path to file
            content: Content to write

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {str(e)}")
            return False
