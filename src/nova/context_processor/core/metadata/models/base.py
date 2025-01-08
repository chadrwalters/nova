"""Base metadata models for Nova document processor."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict


class MetadataVersion(BaseModel):
    """Version information for metadata."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        },
    )

    major: int = Field(default=1, description="Major version number")
    minor: int = Field(default=0, description="Minor version number")
    patch: int = Field(default=0, description="Patch version number")
    timestamp: datetime = Field(default_factory=datetime.now, description="Version timestamp")
    phase: str = Field(description="Processing phase that created this version")
    changes: List[str] = Field(default_factory=list, description="List of changes in this version")

    def __str__(self) -> str:
        """String representation of version."""
        return f"{self.major}.{self.minor}.{self.patch}"


class BaseMetadata(BaseModel):
    """Base metadata model."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            Path: str,
            datetime: lambda v: v.isoformat() if v else None,
            set: list,
        },
    )

    # File information
    file_path: Path = Field(description="Path to file")
    file_name: str = Field(description="Name of file")
    file_type: Optional[str] = Field(None, description="MIME type of file")
    file_size: Optional[int] = Field(None, description="Size of file in bytes")
    file_hash: Optional[str] = Field(None, description="SHA-256 hash of file contents")
    
    # Processing information
    handler_name: str = Field(description="Name of handler that processed file")
    handler_version: str = Field(description="Version of handler that processed file")
    processed_at: datetime = Field(default_factory=datetime.now, description="When file was processed")
    current_version: MetadataVersion = Field(default_factory=lambda: MetadataVersion(phase="unknown"), description="Current version of metadata")
    version_history: List[MetadataVersion] = Field(default_factory=list, description="Version history")
    
    # Content information
    title: Optional[str] = Field(None, description="Title of document")
    description: Optional[str] = Field(None, description="Description of document")
    content: Optional[str] = Field(None, description="Extracted text content")
    tags: Set[str] = Field(default_factory=set, description="Tags for document")
    
    # File relationships
    parent_file: Optional[Path] = Field(None, description="Parent file if this is a child document")
    child_files: Set[Path] = Field(default_factory=set, description="Child files")
    embedded_files: Set[Path] = Field(default_factory=set, description="Embedded files")
    output_files: Set[Path] = Field(default_factory=set, description="Generated output files")
    
    # Error tracking
    has_errors: bool = Field(default=False, description="Whether processing encountered errors")
    error_count: int = Field(default=0, description="Number of errors encountered")
    line_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Line-specific errors")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="General errors")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def __init__(self, **data: Any) -> None:
        """Initialize metadata.

        Args:
            **data: Metadata fields
        """
        super().__init__(**data)
        if not self.file_name and self.file_path:
            self.file_name = self.file_path.name
    
    def add_line_error(self, line_number: int, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a line-specific error.

        Args:
            line_number: Line number where error occurred
            error: Error message
            details: Optional error details
        """
        self.has_errors = True
        self.error_count += 1
        error_entry = {
            "line": line_number,
            "error": error,
            **(details or {})
        }
        self.line_errors.append(error_entry)

    def add_error(self, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a general error.

        Args:
            source: Source of the error (e.g., handler name)
            message: Error message
            details: Optional error details
        """
        self.has_errors = True
        self.error_count += 1
        error_entry = {
            "source": source,
            "message": message,
            "timestamp": datetime.now(),
            **(details or {})
        }
        self.errors.append(error_entry)

    def add_version(self, phase: str, changes: Optional[List[str]] = None) -> None:
        """Add a new version to the history.

        Args:
            phase: Processing phase
            changes: Optional list of changes
        """
        # Create new version
        new_version = MetadataVersion(
            major=self.current_version.major,
            minor=self.current_version.minor + 1,
            patch=0,
            phase=phase,
            changes=changes or []
        )
        
        # Add current version to history
        self.version_history.append(self.current_version)
        
        # Set new version as current
        self.current_version = new_version 