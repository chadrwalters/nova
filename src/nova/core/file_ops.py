import os
import aiofiles
from pathlib import Path
from typing import Optional

from nova.core.logging import get_logger

logger = get_logger(__name__)

class FileOperationsManager:
    """Manages file operations for the document processor."""
    
    def __init__(self):
        """Initialize file operations manager."""
        pass
        
    async def read_file(self, file_path: Path) -> str:
        """Read file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            return None
            
    async def write_file(self, file_path: Path, content: str) -> bool:
        """Write content to file.
        
        Args:
            file_path: Path to file
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {str(e)}")
            return False
            
    async def copy_file(self, src: Path, dst: Path) -> bool:
        """Copy file from source to destination.
        
        Args:
            src: Source path
            dst: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            content = await self.read_file(src)
            if content is None:
                return False
            return await self.write_file(dst, content)
        except Exception as e:
            logger.error(f"Failed to copy file {src} to {dst}: {str(e)}")
            return False
            
    async def path_exists(self, path: Path) -> bool:
        """Check if path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        return path.exists()
        
    async def create_directory(self, path: Path) -> bool:
        """Create directory.
        
        Args:
            path: Path to directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {str(e)}")
            return False 