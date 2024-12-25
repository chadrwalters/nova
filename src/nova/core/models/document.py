"""Document model for Nova document processor."""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class Document(BaseModel):
    """Represents a document in the Nova system."""
    
    # Core attributes
    path: Path = Field(..., description="Path to the document file")
    content: str = Field(default="", description="Document content")
    format: str = Field(default="markdown", description="Document format")
    
    # Metadata
    title: Optional[str] = Field(default=None, description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    created_at: Optional[datetime] = Field(default=None, description="Document creation time")
    modified_at: Optional[datetime] = Field(default=None, description="Document last modification time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Processing state
    processed: bool = Field(default=False, description="Whether document has been processed")
    processing_errors: List[str] = Field(default_factory=list, description="Processing errors")
    processing_warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    
    # References and attachments
    attachments: List[Path] = Field(default_factory=list, description="Paths to attachment files")
    references: Dict[str, str] = Field(default_factory=dict, description="Map of reference IDs to paths")
    image_refs: Dict[str, str] = Field(default_factory=dict, description="Map of image references to paths")
    link_refs: Dict[str, str] = Field(default_factory=dict, description="Map of link references to paths")
    processed_refs: Set[str] = Field(default_factory=set, description="Set of processed reference IDs")
    
    # Content sections
    sections: Dict[str, str] = Field(default_factory=dict, description="Named content sections")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    def add_attachment(self, path: Path) -> None:
        """Add an attachment file.
        
        Args:
            path: Path to attachment file
        """
        if path not in self.attachments:
            self.attachments.append(path)
    
    def add_reference(self, ref_id: str, path: str) -> None:
        """Add a reference.
        
        Args:
            ref_id: Reference ID
            path: Path to referenced file
        """
        self.references[ref_id] = str(path)
    
    def add_image_ref(self, ref_id: str, path: str) -> None:
        """Add an image reference.
        
        Args:
            ref_id: Reference ID
            path: Path to image file
        """
        self.image_refs[ref_id] = str(path)
    
    def add_link_ref(self, ref_id: str, path: str) -> None:
        """Add a link reference.
        
        Args:
            ref_id: Reference ID
            path: Path to linked file
        """
        self.link_refs[ref_id] = str(path)
    
    def mark_ref_processed(self, ref_id: str) -> None:
        """Mark a reference as processed.
        
        Args:
            ref_id: Reference ID
        """
        self.processed_refs.add(ref_id)
    
    def is_ref_processed(self, ref_id: str) -> bool:
        """Check if a reference has been processed.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            True if reference has been processed
        """
        return ref_id in self.processed_refs
    
    def add_section(self, name: str, content: str) -> None:
        """Add a named content section.
        
        Args:
            name: Section name
            content: Section content
        """
        self.sections[name] = content
    
    def get_section(self, name: str) -> Optional[str]:
        """Get a named content section.
        
        Args:
            name: Section name
            
        Returns:
            Section content or None if not found
        """
        return self.sections.get(name)
    
    def add_error(self, error: str) -> None:
        """Add a processing error.
        
        Args:
            error: Error message
        """
        self.processing_errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a processing warning.
        
        Args:
            warning: Warning message
        """
        self.processing_warnings.append(warning)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update document metadata.
        
        Args:
            metadata: Metadata dictionary to update with
        """
        self.metadata.update(metadata)
    
    def set_processing_time(self, seconds: float) -> None:
        """Set document processing time.
        
        Args:
            seconds: Processing time in seconds
        """
        self.processing_time = seconds
        self.processed = True