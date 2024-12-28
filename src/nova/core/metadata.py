from pathlib import Path

class DocumentMetadata:
    @classmethod
    def from_file(cls, file_path: Path, handler_name: str, handler_version: str) -> "DocumentMetadata":
        """Create metadata from file.
        
        Args:
            file_path: Path to file.
            handler_name: Name of handler.
            handler_version: Version of handler.
            
        Returns:
            Document metadata.
        """
        # Convert path to string with Windows encoding
        path_str = str(file_path.absolute())
        safe_path = path_str.encode('cp1252', errors='replace').decode('cp1252')
        
        return cls(
            file_path=safe_path,
            file_name=file_path.name,
            file_type=file_path.suffix.lstrip('.').lower(),
            handler_name=handler_name,
            handler_version=handler_version,
            processed=False,
            error=None,
            metadata={},
        ) 