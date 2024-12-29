from pathlib import Path
from typing import Dict, List, Optional, Any

class FileMetadata:
    """Metadata for a processed file."""
    
    def __init__(self, file_path: Path):
        """Initialize metadata.
        
        Args:
            file_path: Path to file
        """
        self.file_path = file_path
        self.processed = False
        self.unchanged = False
        self.reprocessed = False
        self.output_files = set()
        self.errors = []
        self.metadata: Dict[str, Any] = {}
        self.title: Optional[str] = None
        self.has_errors = False
        
    def add_error(self, handler_name: str, error: str) -> None:
        """Add an error from a handler.
        
        Args:
            handler_name: Name of the handler that encountered the error
            error: Error message
        """
        self.errors[handler_name] = error
        self.has_errors = True
        
    def add_output_file(self, output_file: Path) -> None:
        """Add an output file to the metadata.
        
        Args:
            output_file: Path to output file
        """
        self.output_files.add(output_file)
            
    @classmethod
    def from_file(cls, file_path: Path, handler_name: str, handler_version: str) -> 'FileMetadata':
        """Create metadata from a file.
        
        Args:
            file_path: Path to file
            handler_name: Name of handler
            handler_version: Version of handler
            
        Returns:
            File metadata
        """
        metadata = cls()
        metadata.title = file_path.stem
        metadata.metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_type': file_path.suffix[1:] if file_path.suffix else "",
            'handler_name': handler_name,
            'handler_version': handler_version,
        }
        return metadata 