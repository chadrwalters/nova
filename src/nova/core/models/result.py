"""Processing result model."""

from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ProcessingResult(BaseModel):
    """Result of a processing operation."""
    
    success: bool = Field(default=False, description="Whether the processing was successful")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    processed_files: List[Union[str, Path]] = Field(default_factory=list, description="List of processed file paths")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    content: Optional[Any] = Field(default=None, description="Processed content")
    
    def add_error(self, error: str) -> None:
        """Add an error message.
        
        Args:
            error: Error message to add
        """
        self.errors.append(error)
        self.success = False
        
    def add_processed_file(self, file_path: Union[str, Path]) -> None:
        """Add a processed file path.
        
        Args:
            file_path: Path of processed file
        """
        self.processed_files.append(file_path)
        
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata.
        
        Args:
            metadata: Metadata to update
        """
        self.metadata.update(metadata)
        
    def set_content(self, content: Any) -> None:
        """Set processed content.
        
        Args:
            content: Processed content
        """
        self.content = content
        
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0 