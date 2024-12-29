"""Document metadata model."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


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
        return super().default(obj)


@dataclass
class DocumentMetadata:
    """Document metadata."""
    
    # File information
    file_name: str
    file_path: str
    file_type: str
    
    # Processing information
    handler_name: str
    handler_version: str
    processed: bool = False
    
    # Content information
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    
    # Relationships
    attachments: List["DocumentMetadata"] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Union[str, int, float, bool]] = field(default_factory=dict)
    
    # Error information
    error: Optional[str] = None
    errors: List[Dict[str, str]] = field(default_factory=list)
    
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
        return cls(
            file_name=file_path.name,
            file_path=str(file_path),
            file_type=file_path.suffix[1:] if file_path.suffix else "",
            handler_name=handler_name,
            handler_version=handler_version,
            processed=False,
        )
    
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
        error_dict = {
            "phase": phase,
            "message": error
        }
        self.errors.append(error_dict)
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
        if 'output_files' not in self.metadata:
            self.metadata['output_files'] = []
        self.metadata['output_files'].append(str(output_path))