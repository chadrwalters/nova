"""Base handler for document processing.

This module provides the base class for all document handlers in the Nova system.
Each handler is responsible for processing a specific type of file (PDF, DOCX, etc.)
and converting it to a standardized Markdown format with metadata.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging
import os
from dataclasses import dataclass
from enum import Enum

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from ..cache.manager import CacheManager
from ..utils.output_manager import OutputManager
from nova.utils.file_utils import safe_write_file


class HandlerError(Exception):
    """Base class for handler exceptions."""
    pass

class ValidationError(HandlerError):
    """Raised when file validation fails."""
    pass

class ProcessingError(HandlerError):
    """Raised when file processing fails."""
    pass

class FileTypeError(HandlerError):
    """Raised when file type is not supported."""
    pass

class ProcessingStatus(Enum):
    """Status of file processing."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProcessingResult:
    """Result of file processing."""
    status: ProcessingStatus
    metadata: Optional[DocumentMetadata]
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class BaseHandler(ABC):
    """Base class for document handlers.
    
    This class defines the interface that all handlers must implement.
    It provides common functionality for file handling, validation,
    and error management.
    
    Attributes:
        name (str): Name of the handler
        version (str): Version of the handler
        file_types (List[str]): List of supported file extensions
        config (ConfigManager): Nova configuration
        metadata (DocumentMetadata): Current file metadata
        cache_manager (CacheManager): Cache manager
        output_manager (OutputManager): Output manager
        logger (logging.Logger): Logger instance
    """
    
    name: str
    version: str
    file_types: List[str]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.
        
        Args:
            config: Nova configuration manager
        """
        self.config = config
        self.metadata = None
        self.cache_manager = CacheManager(config)
        self.output_manager = OutputManager(config)
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._processing_status = ProcessingStatus.NOT_STARTED
    
    def validate_file(self, file_path: Path) -> None:
        """Validate file before processing.
        
        Args:
            file_path: Path to file
            
        Raises:
            ValidationError: If file validation fails
            FileTypeError: If file type is not supported
        """
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")
            
        if not file_path.is_file():
            raise ValidationError(f"Not a file: {file_path}")
            
        if not self.supports_file(file_path):
            raise FileTypeError(
                f"Unsupported file type: {file_path.suffix} "
                f"(supported: {', '.join(self.file_types)})"
            )
            
        try:
            # Try to open file to verify permissions
            with open(file_path, 'rb') as _:
                pass
        except Exception as e:
            raise ValidationError(f"Cannot access file: {str(e)}")
    
    def _get_safe_path_str(self, file_path: Union[str, Path]) -> str:
        """Get safe string representation of path.
        
        Args:
            file_path: Path to convert
            
        Returns:
            Safe string representation of path
        """
        if file_path is None:
            return ""
            
        try:
            # Convert to Path object if string
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            # Get absolute path
            file_path = file_path.absolute()
            
            # Convert to string and handle Windows encoding
            path_str = str(file_path)
            return path_str.encode('cp1252', errors='replace').decode('cp1252')
            
        except Exception:
            # If all else fails, use ASCII with replacement
            return str(file_path).encode('ascii', errors='replace').decode('ascii')
                
    def _safe_read_file(self, file_path: Path, mode='r', encoding=None) -> Union[str, bytes]:
        """Safely read a file with proper encoding detection.
        
        Args:
            file_path: Path to file
            mode: File mode ('r' for text, 'rb' for binary)
            encoding: Optional encoding for text mode
            
        Returns:
            File contents as string or bytes
            
        Raises:
            ProcessingError: If file cannot be read
        """
        try:
            # Ensure we have an absolute path
            file_path = file_path.absolute()
            
            if 'b' in mode:
                # Binary mode - return raw bytes
                with open(file_path, mode) as f:
                    return f.read()
            else:
                # Text mode - try encodings
                if encoding:
                    # Try specified encoding first
                    try:
                        with open(file_path, mode, encoding=encoding) as f:
                            return f.read()
                    except UnicodeError:
                        pass
                        
                # Try common encodings
                encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
                for enc in encodings:
                    try:
                        with open(file_path, mode, encoding=enc) as f:
                            return f.read()
                    except UnicodeError:
                        continue
                        
                # Fall back to binary read + decode with replacement
                with open(file_path, 'rb') as f:
                    content = f.read()
                return content.decode('utf-8', errors='replace')
                
        except Exception as e:
            raise ProcessingError(f"Failed to read file {self._get_safe_path_str(file_path)}: {str(e)}") from e
            
    def _safe_write_file(self, file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """Write content to file only if it has changed.
        
        Args:
            file_path: Path to file.
            content: Content to write.
            encoding: File encoding.
            
        Returns:
            True if file was written, False if unchanged.
        """
        return safe_write_file(file_path, content, encoding)

    def _get_relative_path(self, from_path: Path, to_path: Path) -> str:
        """Get relative path from one file to another.
        
        Args:
            from_path: Path to start from.
            to_path: Path to end at.
            
        Returns:
            Relative path from from_path to to_path.
        """
        # Get relative path from markdown file to original file
        try:
            rel_path = os.path.relpath(to_path, from_path.parent)
            return rel_path.replace("\\", "/")  # Normalize path separators
        except ValueError:
            # If paths are on different drives, use absolute path
            return str(to_path).replace("\\", "/")

    def _write_markdown(self, markdown_path: Path, title: str, file_path: Path, content: str, **kwargs) -> bool:
        """Write markdown content to file.
        
        Args:
            markdown_path: Path to write markdown file to
            title: Title for markdown file
            file_path: Path to original file
            content: Processed content
            **kwargs: Additional handler-specific parameters
            
        Returns:
            True if file was written, False if unchanged
        """
        try:
            # Get relative path from markdown to original
            rel_path = self._get_relative_path(markdown_path, file_path)
            
            markdown_content = f"""# {title}

## Content

{content}

[Original File: {file_path.name}]({rel_path})
"""
            
            return self._safe_write_file(markdown_path, markdown_content)
            
        except Exception as e:
            self.logger.error(f"Failed to write markdown for {file_path}: {str(e)}")
            raise

    async def _process_content(self, file_path: Path) -> str:
        """Process file content.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Processed content as string.
            
        This method should be overridden by handlers that need to do special processing.
        The default implementation just reads the file as text.
        """
        return self._safe_read_file(file_path)
            
    def _init_metadata(self, file_path: Path) -> None:
        """Initialize metadata for document.
        
        Args:
            file_path: Path to file.
        """
        try:
            # Ensure we have an absolute path
            file_path = file_path.absolute()
            
            # Get safe path string
            safe_path = self._get_safe_path_str(file_path)
            
            # Create metadata
            self.metadata = DocumentMetadata.from_file(
                Path(safe_path),
                self.name,
                self.version,
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize metadata for {self._get_safe_path_str(file_path)}: {str(e)}") from e
    
    def _update_metadata(self, **kwargs) -> None:
        """Update metadata with additional information.
        
        Args:
            **kwargs: Additional metadata fields.
        """
        if self.metadata is None:
            raise ValueError("Metadata not initialized")
            
        for key, value in kwargs.items():
            setattr(self.metadata, key, value)
    
    async def process(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None,
    ) -> ProcessingResult:
        """Process a file.
        
        This is the main entry point for file processing. It:
        1. Validates the file
        2. Initializes metadata
        3. Calls handler-specific implementation
        4. Handles errors and updates status
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files
            metadata: Optional metadata from previous phase
            
        Returns:
            ProcessingResult with status and metadata
        """
        self._processing_status = ProcessingStatus.IN_PROGRESS
        
        try:
            # Validate file
            try:
                self.validate_file(file_path)
            except (ValidationError, FileTypeError) as e:
                return ProcessingResult(
                    status=ProcessingStatus.SKIPPED,
                    metadata=None,
                    error=str(e)
                )
            
            # Initialize metadata if not provided
            if metadata is None:
                self._init_metadata(file_path)
                metadata = self.metadata
            
            # Process file
            try:
                metadata = await self.process_impl(file_path, metadata)
                if metadata is None:
                    return ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        metadata=None,
                        error="Handler returned None"
                    )
                    
                self._processing_status = ProcessingStatus.COMPLETED
                return ProcessingResult(
                    status=ProcessingStatus.COMPLETED,
                    metadata=metadata
                )
                
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {str(e)}")
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    metadata=metadata,
                    error=str(e)
                )
                
        except Exception as e:
            self.logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=None,
                error=str(e)
            )
            
        finally:
            if self._processing_status != ProcessingStatus.COMPLETED:
                self._processing_status = ProcessingStatus.FAILED

    @abstractmethod
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a file (handler implementation).
        
        This method must be implemented by handlers to provide
        type-specific processing logic.
        
        Args:
            file_path: Path to file to process
            metadata: Document metadata
            
        Returns:
            Updated metadata, or None if processing failed
        """
        raise NotImplementedError()

    def supports_file(self, file_path: Union[str, Path]) -> bool:
        """Check if handler supports given file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file type is supported
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        return file_path.suffix.lower().lstrip('.') in self.file_types 