import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FileMetadata:
    """Metadata for a processed file."""

    def __init__(self, file_path: Path):
        """Initialize metadata.

        Args:
            file_path: Path to file
        """
        self.file_path = file_path
        self.processed = False
        self.unchanged = False
        self.reprocessed = False
        self.output_files = set()
        self.errors: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.title: Optional[str] = None
        self.has_errors = False
        self.links = []

    def add_error(self, handler_name: str, error: str) -> None:
        """Add an error from a handler.

        Args:
            handler_name: Name of the handler that encountered the error
            error: Error message
        """
        self.errors[handler_name] = error
        self.has_errors = True

    def add_output_file(self, output_file: Path) -> None:
        """Add an output file to the metadata.

        Args:
            output_file: Path to output file
        """
        self.output_files.add(output_file)

    def add_link(self, link_context) -> None:
        """Add a link to the document's links.

        Args:
            link_context: Link context to add
        """
        self.links.append(link_context)

    def get_outgoing_links(self) -> List:
        """Get all outgoing links from this document.

        Returns:
            List of link contexts
        """
        return [link for link in self.links if link.source_file == str(self.file_path)]

    def get_incoming_links(self) -> List:
        """Get all incoming links to this document.

        Returns:
            List of link contexts
        """
        return [link for link in self.links if link.target_file == str(self.file_path)]

    def save(self, output_path: Optional[Path] = None) -> None:
        """Save metadata to a file.

        Args:
            output_path: Optional path to save metadata to. If not provided,
                will save to {file_path.stem}.metadata.json in the same directory.
        """
        try:
            # Get metadata file path
            metadata_path = (
                output_path
                if output_path
                else self.file_path.parent / f"{self.file_path.stem}.metadata.json"
            )

            # Convert metadata to dictionary
            metadata_dict = {
                "file_path": str(self.file_path),
                "processed": self.processed,
                "unchanged": self.unchanged,
                "reprocessed": self.reprocessed,
                "output_files": [str(f) for f in self.output_files],
                "errors": self.errors,
                "metadata": self.metadata,
                "title": self.title,
                "has_errors": self.has_errors,
                "links": [link.__dict__ for link in self.links],
                "handler_name": self.handler_name
                if hasattr(self, "handler_name")
                else None,
                "handler_version": self.handler_version
                if hasattr(self, "handler_version")
                else None,
            }

            # Write metadata to file
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to save metadata for {self.file_path}: {str(e)}")
            raise

    @classmethod
    def from_file(
        cls, file_path: Path, handler_name: str, handler_version: str
    ) -> "FileMetadata":
        """Create metadata from a file.

        Args:
            file_path: Path to file
            handler_name: Name of handler
            handler_version: Version of handler

        Returns:
            File metadata
        """
        metadata = cls(file_path)
        metadata.title = file_path.stem
        metadata.metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix[1:] if file_path.suffix else "",
            "handler_name": handler_name,
            "handler_version": handler_version,
        }
        return metadata


class DocumentMetadata(FileMetadata):
    """Metadata for a processed document."""

    def __init__(self, file_path: Path):
        """Initialize document metadata.

        Args:
            file_path: Path to file
        """
        super().__init__(file_path)
        self.sections = []
        self.attachments = []
        self.references = []
        self.summary = None
        self.raw_notes = None

    def get_references(self) -> List:
        """Get all references from this document.

        Returns:
            List of references
        """
        return self.references

    @classmethod
    def from_file(
        cls, file_path: Path, handler_name: str, handler_version: str
    ) -> "DocumentMetadata":
        """Create document metadata from a file.

        Args:
            file_path: Path to file
            handler_name: Name of handler
            handler_version: Version of handler

        Returns:
            Document metadata
        """
        metadata = cls(file_path)
        metadata.title = file_path.stem
        metadata.metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix[1:] if file_path.suffix else "",
            "handler_name": handler_name,
            "handler_version": handler_version,
        }
        return metadata
