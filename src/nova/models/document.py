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
            'output_files': [str(p) for p in self.output_files]
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