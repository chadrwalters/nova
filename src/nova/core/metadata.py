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
        self.errors: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.title: Optional[str] = None
        self.has_errors = False
        self.links = []
        
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

    def add_link(self, link_context) -> None:
        """Add a link to the document's links.
        
        Args:
            link_context: Link context to add
        """
        self.links.append(link_context)
    
    def get_outgoing_links(self) -> List:
        """Get all outgoing links from this document.
        
        Returns:
            List of link contexts
        """
        return [link for link in self.links if link.source_file == str(self.file_path)]
    
    def get_incoming_links(self) -> List:
        """Get all incoming links to this document.
        
        Returns:
            List of link contexts
        """
        return [link for link in self.links if link.target_file == str(self.file_path)]
            
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
        metadata = cls(file_path)
        metadata.title = file_path.stem
        metadata.metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_type': file_path.suffix[1:] if file_path.suffix else "",
            'handler_name': handler_name,
            'handler_version': handler_version,
        }
        return metadata 