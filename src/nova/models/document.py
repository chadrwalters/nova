"""Document metadata model."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set

from .links import LinkMap, LinkContext, LinkType


class NovaJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Nova metadata."""
    
    def default(self, obj):
        """Handle special types.
        
        Args:
            obj: Object to encode.
            
        Returns:
            JSON-serializable object.
        """
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, 'model_dump'):  # Handle Pydantic models
            return obj.model_dump()
        return super().default(obj)


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    
    # File information
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    
    # Processing information
    handler_name: str = ""
    handler_version: str = ""
    processed: bool = False
    unchanged: bool = False
    reprocessed: bool = False
    
    # Content information
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    
    # Relationships
    attachments: List["DocumentMetadata"] = field(default_factory=list)
    
    # Link information
    links: LinkMap = field(default_factory=LinkMap)
    
    # Additional metadata
    metadata: Dict[str, Union[str, int, float, bool]] = field(default_factory=dict)
    
    # Error information
    error: Optional[str] = None
    errors: Dict[str, str] = field(default_factory=dict)
    
    # Output files
    output_files: Set[Path] = field(default_factory=set)
    
    @classmethod
    def from_file(cls, file_path: Path, handler_name: str, handler_version: str) -> "DocumentMetadata":
        """Create metadata from file.
        
        Args:
            file_path: Path to file.
            handler_name: Name of handler processing the file.
            handler_version: Version of handler processing the file.
            
        Returns:
            Document metadata.
        """
        metadata = cls()
        metadata.file_name = file_path.name
        metadata.file_path = str(file_path)
        metadata.file_type = file_path.suffix[1:] if file_path.suffix else ""
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        metadata.title = file_path.stem
        return metadata
    
    @property
    def dict(self) -> Dict:
        """Convert metadata to dictionary.
        
        Returns:
            Dictionary representation of metadata.
        """
        return self.to_dict()
    
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary.
        
        Returns:
            Dictionary representation of metadata.
        """
        data = asdict(self)
        
        # Ensure all string values are UTF-8 safe
        def sanitize_value(value: Any) -> Any:
            if isinstance(value, str):
                return value.encode("utf-8", errors="replace").decode("utf-8")
            elif isinstance(value, list):
                return [sanitize_value(item) for item in value]
            elif isinstance(value, dict):
                return {key: sanitize_value(val) for key, val in value.items()}
            return value
        
        return {key: sanitize_value(value) for key, value in data.items()}
    
    def add_error(self, phase: str, error: str) -> None:
        """Add an error for a phase.
        
        Args:
            phase: Phase name.
            error: Error message.
        """
        self.errors[phase] = error
        if not self.error:
            self.error = error
    
    @property
    def has_errors(self) -> bool:
        """Check if document has any errors.
        
        Returns:
            True if document has errors, False otherwise.
        """
        return len(self.errors) > 0 or self.error is not None

    def add_output_file(self, output_path: Path) -> None:
        """Add an output file path to the metadata.
        
        Args:
            output_path: Path to output file.
        """
        self.output_files.add(output_path)
    
    def add_link(self, link: LinkContext) -> None:
        """Add a link to the document's link map.
        
        Args:
            link: Link context to add
        """
        self.links.add_link(link)
    
    def get_outgoing_links(self) -> List[LinkContext]:
        """Get all outgoing links from this document.
        
        Returns:
            List of link contexts
        """
        return self.links.get_outgoing_links(self.file_path)
    
    def get_incoming_links(self) -> List[LinkContext]:
        """Get all incoming links to this document.
        
        Returns:
            List of link contexts
        """
        return self.links.get_incoming_links(self.file_path)
    
    def get_links_by_type(self, link_type: LinkType) -> List[LinkContext]:
        """Get all links of a specific type.
        
        Args:
            link_type: Type of links to get
            
        Returns:
            List of link contexts
        """
        return self.links.get_links_by_type(link_type)
    
    def validate_links(self) -> List[str]:
        """Validate all links in the document.
        
        Returns:
            List of validation error messages
        """
        return self.links.validate_links()