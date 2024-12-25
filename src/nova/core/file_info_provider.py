"""File information provider module."""

import os
import magic
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FileInfo:
    """File information."""
    path: Path
    content_type: str
    size: int
    metadata: Dict[str, Any]

class FileInfoProvider:
    """Provides file information."""
    
    def __init__(self):
        """Initialize file info provider."""
        self.magic = magic.Magic(mime=True)
    
    async def get_file_info(self, file_path: Path) -> FileInfo:
        """Get file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileInfo object containing file information
        """
        try:
            # Get basic file info
            stat = file_path.stat()
            
            # Get content type
            content_type = self.magic.from_file(str(file_path))
            
            # Get metadata
            metadata = {
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
                'extension': file_path.suffix.lower(),
                'name': file_path.name
            }
            
            return FileInfo(
                path=file_path,
                content_type=content_type,
                size=stat.st_size,
                metadata=metadata
            )
            
        except Exception as e:
            raise Exception(f"Failed to get file info for {file_path}: {str(e)}") 