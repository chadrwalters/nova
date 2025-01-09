"""Base metadata model for Nova document processor."""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel, Field


class BaseMetadata(BaseModel):
    """Base metadata model."""

    # File information
    file_path: str = Field(..., description="Path to original file")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., description="File size in bytes")
    file_hash: str = Field(..., description="SHA-256 hash of file contents")
    created_at: float = Field(..., description="File creation time")
    modified_at: float = Field(..., description="File modification time")

    # Content information
    title: Optional[str] = Field(None, description="Title of document")
    content: Optional[str] = Field(None, description="Extracted text content")
    line_count: Optional[int] = Field(None, description="Number of lines")
    word_count: Optional[int] = Field(None, description="Number of words")
    char_count: Optional[int] = Field(None, description="Number of characters")
    sheet_count: Optional[int] = Field(None, description="Number of sheets")
    total_rows: Optional[int] = Field(None, description="Total number of rows")
    total_columns: Optional[int] = Field(None, description="Total number of columns")

    # Image information
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    format: Optional[str] = Field(None, description="Image format")
    color_space: Optional[str] = Field(None, description="Color space")
    has_alpha: Optional[bool] = Field(None, description="Whether image has alpha channel")
    dpi: Optional[int] = Field(None, description="Dots per inch")

    # Document-specific fields
    has_frontmatter: Optional[bool] = Field(None, description="Whether markdown has frontmatter")
    has_code_blocks: Optional[bool] = Field(None, description="Whether document has code blocks")
    has_links: Optional[bool] = Field(None, description="Whether document has links")
    has_images: Optional[bool] = Field(None, description="Whether document has images")
    has_formulas: Optional[bool] = Field(None, description="Whether spreadsheet has formulas")
    has_macros: Optional[bool] = Field(None, description="Whether spreadsheet has macros")
    charset: Optional[str] = Field(None, description="Character encoding of the document")
    images: Optional[List[str]] = Field(None, description="List of image paths in HTML")
    scripts: Optional[List[str]] = Field(None, description="List of script paths in HTML")
    styles: Optional[List[str]] = Field(None, description="List of style paths in HTML")

    # File relationships
    links: Optional[List[str]] = Field(None, description="External links")
    output_files: Set[str] = Field(default_factory=set, description="Output files generated during processing")
    output_dir: Optional[str] = Field(None, description="Output directory for processed files")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Errors encountered during processing")
    changes: List[str] = Field(default_factory=list, description="Changes made during processing")

    def add_error(self, handler: str, error: str) -> None:
        """Add an error to the metadata.

        Args:
            handler: Handler that encountered the error
            error: Error message
        """
        self.errors.append({
            "handler": handler,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def add_version(self, phase: str, changes: List[str]) -> None:
        """Add version information to metadata.

        Args:
            phase: Phase that made the changes
            changes: List of changes made
        """
        self.changes.extend([f"[{phase}] {change}" for change in changes])

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary.

        Returns:
            Dictionary representation of metadata
        """
        data = self.model_dump()
        # Convert set to list for JSON serialization
        data["output_files"] = list(data["output_files"])
        return data 