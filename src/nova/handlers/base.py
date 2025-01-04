"""Base handler for file processing."""

from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union
from ..models.document import DocumentMetadata
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..utils.path_utils import ensure_parent_dirs, get_safe_path
from ..utils.output_manager import OutputManager


class ProcessingStatus:
    """Status of file processing."""
    
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNCHANGED = "unchanged"


class ProcessingResult:
    """Result of file processing."""
    
    def __init__(self, status: str, metadata: Optional[DocumentMetadata] = None, error: Optional[str] = None):
        """Initialize result.
        
        Args:
            status: Processing status
            metadata: Document metadata
            error: Error message if any
        """
        self.status = status
        self.metadata = metadata
        self.error = error


class BaseHandler(ABC):
    """Base class for file handlers."""
    
    name = "base"
    version = "0.1.0"
    file_types: List[str] = []
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.
        
        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.markdown_writer = MarkdownWriter()
        self.output_manager = OutputManager(config)
        
    def supports_file(self, file_path: Path) -> bool:
        """Check if handler supports a file type.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file type is supported
        """
        return file_path.suffix.lstrip('.').lower() in self.file_types
        
    async def process(self, file_path: Path, metadata: DocumentMetadata) -> ProcessingResult:
        """Process a file.
        
        Args:
            file_path: Path to file
            metadata: Document metadata
            
        Returns:
            Processing result
        """
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error=f"File not found: {file_path}"
                )
                
            if not os.access(file_path, os.R_OK):
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error=f"Cannot access file: {file_path}"
                )
                
            # Process the file
            updated_metadata = await self.process_impl(file_path, metadata)
            
            if updated_metadata is None:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error=f"Failed to process file: {file_path}"
                )
                
            if updated_metadata.errors:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    metadata=updated_metadata,
                    error=str(updated_metadata.errors[0])
                )
                
            return ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                metadata=updated_metadata
            )
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error=error_msg
            )
    
    @abstractmethod
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a file implementation.
        
        Args:
            file_path: Path to file
            metadata: Document metadata
            
        Returns:
            Updated document metadata
        """
        pass
        
    def _safe_write_file(self, file_path: Path, content: str) -> bool:
        """Safely write content to a file.
        
        Args:
            file_path: Path to write to
            content: Content to write
            
        Returns:
            True if file was written
        """
        try:
            # Ensure parent directories exist
            ensure_parent_dirs(file_path)
            
            # Write content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {str(e)}")
            return False
            
    def _save_metadata(self, file_path: Path, relative_path: Path, metadata: DocumentMetadata) -> None:
        """Save metadata to file.
        
        Args:
            file_path: Original file path
            relative_path: Relative path from input directory
            metadata: Document metadata
        """
        try:
            # Get metadata path
            metadata_path = self.output_manager.get_output_path_for_phase(
                relative_path,
                "parse",
                ".metadata.json"
            )
            
            # Save metadata
            metadata.save(metadata_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata for {file_path}: {str(e)}")
            
    def _get_relative_path(self, from_path: Path, to_path: Path) -> Path:
        """Get relative path between two paths.
        
        Args:
            from_path: Source path
            to_path: Target path
            
        Returns:
            Relative path
        """
        try:
            return Path(os.path.relpath(to_path, from_path.parent))
        except Exception:
            return to_path 