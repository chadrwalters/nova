"""Document metadata model."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

class DocumentMetadata:
    """Document metadata."""
    
    def __init__(self, title: str = "") -> None:
        """Initialize document metadata.
        
        Args:
            title: Document title.
        """
        self.title = title
        self.processed = False
        self.metadata: Dict[str, Union[str, int, float, bool, List, Dict]] = {}
        self.errors: List[Dict[str, str]] = []
        self.output_files: List[Path] = []
        self.handler_name: Optional[str] = None
        self.handler_version: Optional[str] = None
        self.file_path: Optional[Path] = None
        self.unchanged = False
        self.reprocessed = False
        self.references: Dict[str, str] = {}  # Map of reference markers to their types (e.g., "IMG", "DOC", etc.)
        
    @classmethod
    def from_file(cls, file_path: Path, handler_name: Optional[str] = None, handler_version: Optional[str] = None) -> 'DocumentMetadata':
        """Create metadata from file.
        
        Args:
            file_path: Path to file.
            handler_name: Optional handler name.
            handler_version: Optional handler version.
            
        Returns:
            Document metadata.
        """
        metadata = cls(title=file_path.stem)
        metadata.file_path = file_path
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        return metadata
        
    def add_error(self, handler: str, message: str) -> None:
        """Add error message.
        
        Args:
            handler: Handler name.
            message: Error message.
        """
        self.errors.append({
            'handler': handler,
            'message': message
        })
        
    def add_output_file(self, file_path: Path) -> None:
        """Add output file.
        
        Args:
            file_path: Output file path.
        """
        self.output_files.append(file_path)
        
    def get_references(self) -> Dict[str, str]:
        """Get document references.
        
        Returns:
            Dictionary mapping reference markers to their types.
        """
        return self.references
        
    def to_json(self) -> str:
        """Convert metadata to JSON string.
        
        Returns:
            JSON string.
        """
        data = {
            'title': self.title,
            'processed': self.processed,
            'metadata': self.metadata,
            'errors': self.errors,
            'output_files': [str(p) for p in self.output_files],
            'handler_name': self.handler_name,
            'handler_version': self.handler_version,
            'file_path': str(self.file_path) if self.file_path else None,
            'unchanged': self.unchanged,
            'reprocessed': self.reprocessed,
            'references': self.references
        }
        return json.dumps(data, indent=2)
        
    def save(self, file_path: Path) -> None:
        """Save metadata to file.
        
        Args:
            file_path: Output file path.
        """
        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write metadata to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())