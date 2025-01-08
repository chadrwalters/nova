"""Metadata models for Nova document processor."""

import json
import logging
import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class LinkContext:
    """Context for a link between documents."""

    source_file: str
    target_file: str
    link_text: str
    link_url: str
    context: str = ""


@dataclass
class FileMetadata:
    """Metadata for a file."""

    file_path: Path
    handler_name: str = ""
    handler_version: str = ""
    processed: bool = False
    unchanged: bool = False
    reprocessed: bool = False
    title: str = ""
    has_errors: bool = False
    has_assets: bool = False
    links: List[LinkContext] = field(default_factory=list)
    output_files: Set[Path] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self):
        """Initialize metadata after creation."""
        # Ensure file_path is a Path object
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)

        # Initialize metadata dict if needed
        if not self.metadata:
            self.metadata = {
                "version": "1.0",  # Metadata schema version
                "phase": "init",  # Initial phase
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "processing_history": [],  # Track processing steps
                "errors": [],  # Structured error tracking
                "stats": {},  # File-type specific statistics
                "checksum": None,  # Will be set during processing
                "file_info": {  # Basic file information
                    "name": self.file_path.name,
                    "extension": self.file_path.suffix[1:] if self.file_path.suffix else "",
                    "size": None,  # Will be set during processing
                    "created": None,  # Will be set during processing
                    "modified": None,  # Will be set during processing
                }
            }

        # Initialize output_files set if needed
        if not self.output_files:
            self.output_files = set()

        # Initialize errors list if needed
        if not self.errors:
            self.errors = []

        # Initialize links list if needed
        if not self.links:
            self.links = []

    @classmethod
    def from_file(cls, file_path: Path, handler_name: str, handler_version: str) -> "FileMetadata":
        """Create metadata instance from file.
        
        Args:
            file_path: Path to file
            handler_name: Name of handler
            handler_version: Version of handler
            
        Returns:
            FileMetadata instance
        """
        metadata = cls(file_path)
        metadata.title = file_path.stem
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        
        # Calculate file stats
        try:
            stat = file_path.stat()
            metadata.metadata["file_info"].update({
                "size": stat.st_size,
                "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
            
            # Calculate checksum
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            metadata.metadata["checksum"] = sha256_hash.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to get file stats for {file_path}: {str(e)}")
        
        return metadata

    @classmethod
    def from_json_file(cls, file_path: Path) -> "FileMetadata":
        """Create metadata instance from JSON file.
        
        Args:
            file_path: Path to JSON metadata file
            
        Returns:
            FileMetadata instance
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert paths from strings to Path objects
            if "file_path" in data:
                data["file_path"] = Path(data["file_path"])
            if "output_files" in data:
                data["output_files"] = {Path(p) for p in data["output_files"]}

            # Convert links data to LinkContext objects
            if "links" in data:
                data["links"] = [LinkContext(**link) for link in data["links"]]

            # Ensure required fields exist
            required_fields = ["file_path", "handler_name", "handler_version"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            return cls(**data)

        except Exception as e:
            raise ValueError(f"Failed to load metadata from {file_path}: {str(e)}")

    def add_output_file(self, file_path: Union[str, Path]) -> None:
        """Add an output file to the metadata.

        Args:
            file_path: Path to output file
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        with self._lock:
            self.output_files.add(file_path)
            self.metadata["updated_at"] = datetime.datetime.now().isoformat()

    def add_error(self, handler_name: str, error_msg: str) -> None:
        """Add an error message to the metadata.

        Args:
            handler_name: Name of handler reporting error
            error_msg: Error message
        """
        with self._lock:
            error_entry = {
                "handler": handler_name,
                "message": error_msg,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.metadata["errors"].append(error_entry)
            error_str = f"{handler_name}: {error_msg}"
            if error_str not in self.errors:
                self.errors.append(error_str)
            self.has_errors = True
            self.metadata["updated_at"] = datetime.datetime.now().isoformat()

    def add_processing_step(self, handler_name: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a processing step to the history.

        Args:
            handler_name: Name of handler performing the action
            action: Description of the action
            details: Optional additional details about the action
        """
        with self._lock:
            step = {
                "handler": handler_name,
                "action": action,
                "timestamp": datetime.datetime.now().isoformat()
            }
            if details:
                step["details"] = details
            self.metadata["processing_history"].append(step)
            self.metadata["updated_at"] = datetime.datetime.now().isoformat()

    def update_phase(self, phase: str) -> None:
        """Update the processing phase.

        Args:
            phase: New phase name
        """
        with self._lock:
            self.metadata["phase"] = phase
            self.metadata["updated_at"] = datetime.datetime.now().isoformat()
            self.add_processing_step(
                self.handler_name,
                f"Phase changed to {phase}"
            )

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Update file-type specific statistics.

        Args:
            stats: Dictionary of statistics to update
        """
        with self._lock:
            self.metadata["stats"].update(stats)
            self.metadata["updated_at"] = datetime.datetime.now().isoformat()

    def validate(self) -> bool:
        """Validate metadata.

        Returns:
            True if metadata is valid, False otherwise.
        """
        try:
            # Check required fields
            if not self.file_path or not isinstance(self.file_path, Path):
                self.add_error("validator", "Missing or invalid file_path")
                return False

            if not self.handler_name:
                self.add_error("validator", "Missing handler_name")
                return False

            if not self.handler_version:
                self.add_error("validator", "Missing handler_version")
                return False

            # Validate output files
            for output_file in self.output_files:
                if not isinstance(output_file, Path):
                    self.add_error("validator", f"Invalid output file path: {output_file}")
                    return False

            # Validate links
            for link in self.links:
                if not isinstance(link, LinkContext):
                    self.add_error("validator", f"Invalid link: {link}")
                    return False

            # Validate metadata structure
            required_metadata = ["version", "phase", "created_at", "updated_at", "processing_history", "errors", "stats", "checksum", "file_info"]
            for field in required_metadata:
                if field not in self.metadata:
                    self.add_error("validator", f"Missing required metadata field: {field}")
                    return False

            return True

        except Exception as e:
            self.add_error("validator", f"Validation failed: {str(e)}")
            return False

    def save(self, file_path: Union[str, Path]) -> None:
        """Save metadata to JSON file.

        Args:
            file_path: Path to save metadata to
        """
        try:
            if isinstance(file_path, str):
                file_path = Path(file_path)

            # Validate before saving
            if not self.validate():
                raise ValueError("Metadata validation failed")

            with self._lock:
                # Update timestamp
                self.metadata["updated_at"] = datetime.datetime.now().isoformat()

                # Convert paths to strings for JSON serialization
                data = {
                    "file_path": str(self.file_path),
                    "handler_name": self.handler_name,
                    "handler_version": self.handler_version,
                    "processed": self.processed,
                    "unchanged": self.unchanged,
                    "reprocessed": self.reprocessed,
                    "title": self.title,
                    "has_errors": self.has_errors,
                    "has_assets": self.has_assets,
                    "links": [vars(link) for link in self.links],
                    "output_files": [str(p) for p in self.output_files],
                    "metadata": self.metadata,
                    "errors": self.errors,
                }

                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write metadata file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

        except Exception as e:
            raise ValueError(f"Failed to save metadata to {file_path}: {str(e)}")


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
