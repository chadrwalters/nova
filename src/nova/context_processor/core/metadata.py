import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class LinkContext:
    """Context for a link between documents."""

    source_file: str
    target_file: str
    link_text: str
    link_url: str
    context: str = ""


class FileMetadata:
    """Metadata for a processed file."""

    def __init__(self, file_path: Path):
        """Initialize metadata.

        Args:
            file_path: Path to file
        """
        self.file_path: Path = file_path
        self.processed: bool = False
        self.unchanged: bool = False
        self.reprocessed: bool = False
        self.output_files: Set[Path] = set()
        self.errors: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.title: Optional[str] = None
        self.has_errors: bool = False
        self.links: List[LinkContext] = []
        self.handler_name: Optional[str] = None
        self.handler_version: Optional[str] = None

    @classmethod
    def parse_raw(cls, data: str) -> "FileMetadata":
        """Parse metadata from JSON string.

        Args:
            data: JSON string containing metadata

        Returns:
            FileMetadata object
        """
        json_data = json.loads(data)
        metadata = cls(Path(json_data["file_path"]))
        metadata.processed = json_data.get("processed", False)
        metadata.unchanged = json_data.get("unchanged", False)
        metadata.reprocessed = json_data.get("reprocessed", False)
        metadata.output_files = {Path(p) for p in json_data.get("output_files", [])}
        metadata.errors = json_data.get("errors", {})
        metadata.metadata = json_data.get("metadata", {})
        metadata.title = json_data.get("title")
        metadata.has_errors = json_data.get("has_errors", False)
        metadata.links = [LinkContext(**link) for link in json_data.get("links", [])]
        metadata.handler_name = json_data.get("handler_name")
        metadata.handler_version = json_data.get("handler_version")
        return metadata

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

    def add_link(self, link_context: LinkContext) -> None:
        """Add a link to the document's links.

        Args:
            link_context: Link context to add
        """
        self.links.append(link_context)

    def get_outgoing_links(self) -> List[LinkContext]:
        """Get all outgoing links from this document.

        Returns:
            List of link contexts where this document is the source
        """
        return [link for link in self.links if link.source_file == str(self.file_path)]

    def get_incoming_links(self) -> List[LinkContext]:
        """Get all incoming links to this document.

        Returns:
            List of link contexts where this document is the target
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
                "handler_name": self.handler_name,
                "handler_version": self.handler_version,
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
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        metadata.metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix[1:] if file_path.suffix else "",
            "handler_name": handler_name,
            "handler_version": handler_version,
        }
        return metadata


@dataclass
class Section:
    """A section in a document."""

    title: str
    content: str
    level: int = 1
    subsections: List["Section"] = None

    def __post_init__(self) -> None:
        """Initialize subsections if not provided."""
        if self.subsections is None:
            self.subsections = []


class DocumentMetadata(FileMetadata):
    """Metadata for a processed document."""

    def __init__(self, file_path: Path):
        """Initialize document metadata.

        Args:
            file_path: Path to file
        """
        super().__init__(file_path)
        self.sections: List[Section] = []
        self.attachments: List[Path] = []
        self.references: List[str] = []
        self.summary: Optional[str] = None
        self.raw_notes: Optional[str] = None
        self.output_path: Optional[Path] = None

    def get_references(self) -> List[str]:
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
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        metadata.metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix[1:] if file_path.suffix else "",
            "handler_name": handler_name,
            "handler_version": handler_version,
        }
        return metadata
