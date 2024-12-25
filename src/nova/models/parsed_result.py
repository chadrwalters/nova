"""Models for parse phase results."""

from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, ValidationError

from ..core.errors import (
    ParseError, ValidationError, HandlerError, AttachmentError,
    AttachmentNotFoundError, AttachmentProcessingError
)

class ParsedResult(BaseModel):
    """Result of parsing a markdown file."""
    input_file: Path = Field(..., description="Path to input file")
    output_file: Optional[Path] = Field(None, description="Path to output file")
    content: str = Field("", description="Parsed content")
    source_file: Optional[Path] = Field(None, description="Original source file")
    summary_blocks: List[str] = Field(default_factory=list, description="Summary blocks")
    raw_notes: List[str] = Field(default_factory=list, description="Raw notes")
    attachments: List[Path] = Field(default_factory=list, description="Attachment paths")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    combined_markdown: Optional[str] = Field(None, description="Combined markdown content")
    error: Optional[str] = Field(None, description="Error message if processing failed")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

    def merge(self, other: 'ParsedResult') -> 'ParsedResult':
        """Merge another ParsedResult into this one.
        
        Args:
            other: ParsedResult to merge
            
        Returns:
            Merged ParsedResult
            
        Raises:
            ParseError: If merge fails
            ValidationError: If validation fails
        """
        try:
            # Merge lists
            self.summary_blocks.extend(other.summary_blocks)
            self.raw_notes.extend(other.raw_notes)
            self.attachments.extend(other.attachments)
            
            # Merge metadata
            self.metadata.update(other.metadata)
            
            # Combine content if needed
            if other.content and not self.content:
                self.content = other.content
            elif other.content:
                self.content += f"\n\n{other.content}"
                
            # Update combined markdown
            if other.combined_markdown:
                if not self.combined_markdown:
                    self.combined_markdown = other.combined_markdown
                else:
                    self.combined_markdown += f"\n\n{other.combined_markdown}"
                    
            return self
        except Exception as e:
            raise ParseError(f"Failed to merge ParsedResults: {str(e)}") from e

    def update_attachment_paths(self, new_base_path: Path) -> None:
        """Update attachment paths to use new base path.
        
        Args:
            new_base_path: New base path for attachments
            
        Raises:
            AttachmentError: If path update fails
            AttachmentNotFoundError: If attachment file not found
        """
        try:
            updated_paths: List[Path] = []
            for path in self.attachments:
                new_path = new_base_path / path.name
                if not path.exists():
                    raise AttachmentNotFoundError(f"Attachment not found: {path}")
                updated_paths.append(new_path)
            self.attachments = updated_paths
        except AttachmentNotFoundError:
            raise
        except Exception as e:
            raise AttachmentError(f"Failed to update attachment paths: {str(e)}") from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
            
        Raises:
            ValidationError: If conversion fails
        """
        try:
            return {
                'input_file': str(self.input_file),
                'output_file': str(self.output_file) if self.output_file else None,
                'content': self.content,
                'source_file': str(self.source_file) if self.source_file else None,
                'summary_blocks': self.summary_blocks,
                'raw_notes': self.raw_notes,
                'attachments': [str(p) for p in self.attachments],
                'metadata': self.metadata,
                'combined_markdown': self.combined_markdown,
                'error': self.error
            }
        except Exception as e:
            raise ValidationError(f"Failed to convert ParsedResult to dict: {str(e)}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedResult':
        """Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            ParsedResult instance
            
        Raises:
            ValidationError: If conversion fails
        """
        try:
            # Convert path strings back to Path objects
            if 'input_file' in data:
                data['input_file'] = Path(data['input_file'])
            if 'output_file' in data and data['output_file']:
                data['output_file'] = Path(data['output_file'])
            if 'source_file' in data and data['source_file']:
                data['source_file'] = Path(data['source_file'])
            if 'attachments' in data:
                data['attachments'] = [Path(p) for p in data['attachments']]
                
            return cls(**data)
        except Exception as e:
            raise ValidationError(f"Failed to create ParsedResult from dict: {str(e)}") from e 