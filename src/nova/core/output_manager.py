"""Manages output directory structure and file organization."""

import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

from .logging import get_logger
from .errors import FileError, with_retry, handle_errors
from .utils.file_ops import FileOperationsManager

logger = get_logger(__name__)

@dataclass
class OutputPaths:
    """Container for output directory paths."""
    
    # Base directory for all output
    base_dir: Path
    
    @classmethod
    def from_base(cls, base_dir: Path) -> 'OutputPaths':
        """Create OutputPaths from base directory.
        
        Args:
            base_dir: Base output directory
            
        Returns:
            Configured OutputPaths instance
        """
        return cls(base_dir=base_dir)

class OutputManager:
    """Manages output directory structure and file organization."""
    
    def __init__(self, base_dir: Path):
        """Initialize output manager.
        
        Args:
            base_dir: Base output directory
        """
        self.paths = OutputPaths.from_base(base_dir)
        self._file_ops = FileOperationsManager()
        self._setup_directories()
    
    async def _setup_directories(self) -> None:
        """Create required directory structure."""
        await self._file_ops.create_directory(self.paths.base_dir)
    
    def get_markdown_dir(self, markdown_file: Path) -> Path:
        """Get the directory for a markdown file's attachments.
        
        Args:
            markdown_file: Path to the markdown file
            
        Returns:
            Path to the markdown file's directory
        """
        # Create a directory with same name as markdown file (without extension)
        return self.paths.base_dir / markdown_file.stem
    
    @with_retry()
    @handle_errors()
    async def save_markdown(
        self,
        content: str,
        relative_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Save processed markdown file.
        
        Args:
            content: Markdown content
            relative_path: Original file path relative to input directory
            metadata: Optional metadata to save
            
        Returns:
            Path to saved file
        """
        # Create markdown file path
        output_path = self.paths.base_dir / relative_path
        await self._file_ops.create_directory(output_path.parent)
        
        # Create markdown's attachments directory
        markdown_dir = self.get_markdown_dir(output_path)
        await self._file_ops.create_directory(markdown_dir)
        
        # Save markdown content
        await self._file_ops.write_file(output_path, content)
        
        # Save metadata if provided
        if metadata:
            meta_path = output_path.with_suffix('.meta.json')
            await self._file_ops.write_json_file(meta_path, metadata)
        
        return output_path
    
    @with_retry()
    @handle_errors()
    async def save_attachment(
        self,
        markdown_file: Path,
        attachment_path: Path,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Save an attachment for a markdown file.
        
        Args:
            markdown_file: Path to the parent markdown file
            attachment_path: Original path of the attachment
            content: Attachment content as bytes
            metadata: Optional metadata to save
            
        Returns:
            Path to saved attachment
        """
        # Get markdown's directory for attachments
        markdown_dir = self.get_markdown_dir(markdown_file)
        await self._file_ops.create_directory(markdown_dir)
        
        # Create attachment path
        output_path = markdown_dir / attachment_path.name
        
        # Save attachment content
        await self._file_ops.write_binary_file(output_path, content)
        
        # Save metadata if provided
        if metadata:
            meta_path = output_path.with_suffix('.meta.json')
            await self._file_ops.write_json_file(meta_path, metadata)
        
        return output_path

__all__ = ['OutputManager', 'OutputPaths'] 