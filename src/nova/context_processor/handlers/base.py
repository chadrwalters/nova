"""Base handler for file processing."""

# Standard library
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union
import re

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..core.metadata import DocumentMetadata
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
        self.pipeline = None  # Will be set by HandlerRegistry

    def supports_file(self, file_path: Path) -> bool:
        """Check if handler supports file type.

        Args:
            file_path: Path to file

        Returns:
            True if handler supports file type
        """
        return file_path.suffix.lstrip(".").lower() in self.file_types

    async def process(
        self, file_path: Path, metadata: DocumentMetadata, output_path: Optional[Path] = None
    ) -> ProcessingResult:
        """Process a file.

        Args:
            file_path: Path to file
            metadata: Document metadata
            output_path: Optional output path. If not provided, will be calculated.

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

            # Get relative path from input directory
            rel_path = self._get_relative_path(file_path)

            # Use provided output path or calculate it
            if output_path is None:
                output_path = self._get_output_path(rel_path, "parse", ".parsed.md")

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

            # Save metadata using relative path
            self._save_metadata(file_path, rel_path, updated_metadata)

            return ProcessingResult(
                status=ProcessingStatus.COMPLETED, metadata=updated_metadata
            )

        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error=f"Failed to process file {file_path}: {str(e)}",
            )

    def _get_relative_path(self, file_path: Path) -> Path:
        """Get relative path from input directory.

        Args:
            file_path: Path to file

        Returns:
            Relative path from input directory
        """
        # Convert to Path objects and resolve
        file_path = Path(file_path).resolve()
        input_dir = Path(self.config.input_dir).resolve()

        try:
            # Try to get relative path from input directory
            rel_path = file_path.relative_to(input_dir)
        except ValueError:
            # If file is not under input directory, try to find a parent directory
            # that matches the input directory pattern
            for parent in file_path.parents:
                if re.search(r"\d{8}", str(parent)):
                    # Get the path relative to this parent
                    remaining_path = file_path.relative_to(parent)
                    # Include the parent directory name in the relative path
                    rel_path = Path(parent.name) / remaining_path
                    break
            else:
                # If no parent with date found, use just the filename
                self.logger.warning(f"File {file_path} is not under input directory {input_dir}")
                rel_path = Path(file_path.name)

        return rel_path

    def _get_output_path(self, rel_path: Path, phase: str, suffix: str) -> Path:
        """Get output path for a file.

        Args:
            rel_path: Relative path from input directory
            phase: Pipeline phase
            suffix: File suffix

        Returns:
            Output path
        """
        # Get parent directory structure
        parent_dirs = rel_path.parent

        # Build output path under phase directory
        output_path = Path(self.pipeline.output_manager.get_phase_dir(phase))

        # Add parent directories if they exist
        if str(parent_dirs) != ".":
            # Extract date directory if it exists (format: YYYYMMDD)
            date_match = re.search(r"(\d{8})", str(parent_dirs))
            if date_match:
                # Find the directory containing the date
                date_dir = next((p for p in parent_dirs.parts if date_match.group(1) in p), None)
                if date_dir:
                    # Use the entire directory name containing the date
                    output_path = output_path / date_dir
                    # Add any remaining subdirectories after the date directory
                    remaining_parts = list(parent_dirs.parts)
                    date_dir_index = remaining_parts.index(date_dir)
                    if date_dir_index + 1 < len(remaining_parts):
                        output_path = output_path.joinpath(*remaining_parts[date_dir_index + 1:])
            else:
                output_path = output_path / parent_dirs

        # Add filename with suffix
        output_path = output_path / f"{rel_path.stem}{suffix}"

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
        # Get parent directory structure from relative path
        parent_dirs = relative_path.parent

        # Build output path under phase directory
        output_path = Path(self.output_manager.get_phase_dir("parse"))

        # Add parent directories if they exist
        if str(parent_dirs) != ".":
            # Extract date directory if it exists (format: YYYYMMDD)
            date_match = re.search(r"(\d{8})", str(parent_dirs))
            if date_match:
                # Find the directory containing the date
                date_dir = next((p for p in parent_dirs.parts if date_match.group(1) in p), None)
                if date_dir:
                    # Use the entire directory name containing the date
                    output_path = output_path / date_dir
                    # Add any remaining subdirectories after the date directory
                    remaining_parts = list(parent_dirs.parts)
                    date_dir_index = remaining_parts.index(date_dir)
                    if date_dir_index + 1 < len(remaining_parts):
                        output_path = output_path.joinpath(*remaining_parts[date_dir_index + 1:])
            else:
                output_path = output_path / parent_dirs

        # Add filename with metadata suffix
        metadata_path = output_path / f"{relative_path.stem}.metadata.json"

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
