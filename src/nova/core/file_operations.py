"""File operations manager for the pipeline."""

import os
import shutil
import aiofiles
from pathlib import Path
from typing import List, Optional, Union

from .errors import FileError
from .logging import get_logger

logger = get_logger(__name__)

class FileOperationsManager:
    """Manages file operations for the pipeline."""
    
    def __init__(self, base_dir: Union[str, Path]):
        """Initialize the file operations manager.
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise FileError(f"Base directory does not exist: {self.base_dir}")
    
    def ensure_directory(self, directory: Union[str, Path]) -> Path:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: Directory path to ensure exists
            
        Returns:
            Path to the directory
            
        Raises:
            FileError: If directory cannot be created
        """
        directory = Path(directory)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        except Exception as e:
            raise FileError(f"Failed to create directory: {directory}", details={"error": str(e)})
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False) -> Path:
        """Copy a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to the copied file
            
        Raises:
            FileError: If file cannot be copied
        """
        source = Path(source)
        destination = Path(destination)
        
        try:
            if not source.exists():
                raise FileError(f"Source file does not exist: {source}")
                
            if destination.exists() and not overwrite:
                raise FileError(f"Destination file already exists: {destination}")
                
            destination.parent.mkdir(parents=True, exist_ok=True)
            return Path(shutil.copy2(source, destination))
            
        except Exception as e:
            raise FileError(f"Failed to copy file from {source} to {destination}", details={"error": str(e)})
    
    def read_file_sync(self, file_path: Union[str, Path]) -> str:
        """Read file content synchronously.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
            
        Raises:
            FileError: If file cannot be read
        """
        file_path = Path(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise FileError(f"Failed to read file {file_path}", details={"error": str(e)})
    
    def write_file_sync(self, file_path: Union[str, Path], content: str) -> Path:
        """Write content to file synchronously.
        
        Args:
            file_path: Path to file
            content: Content to write
            
        Returns:
            Path to the written file
            
        Raises:
            FileError: If file cannot be written
        """
        file_path = Path(file_path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return file_path
        except Exception as e:
            raise FileError(f"Failed to write file {file_path}", details={"error": str(e)})
    
    async def read_file(self, file_path: Union[str, Path]) -> str:
        """Read file content asynchronously.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
            
        Raises:
            FileError: If file cannot be read
        """
        file_path = Path(file_path)
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            raise FileError(f"Failed to read file {file_path}", details={"error": str(e)})
    
    async def write_file(self, file_path: Union[str, Path], content: str) -> Path:
        """Write content to file asynchronously.
        
        Args:
            file_path: Path to file
            content: Content to write
            
        Returns:
            Path to the written file
            
        Raises:
            FileError: If file cannot be written
        """
        file_path = Path(file_path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            return file_path
        except Exception as e:
            raise FileError(f"Failed to write file {file_path}", details={"error": str(e)}) 