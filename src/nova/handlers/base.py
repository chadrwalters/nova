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
from ..core.markdown import MarkdownWriter
from ..utils.file_utils import safe_write_file
from ..utils.path_utils import (
    get_safe_path,
    get_metadata_path,
    get_markdown_path,
    ensure_parent_dirs,
    get_relative_path
)


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
        markdown_writer (MarkdownWriter): Markdown generation utility
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
        self.markdown_writer = MarkdownWriter()
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
            
        return str(get_safe_path(file_path))

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
            # Get safe path
            file_path = get_safe_path(file_path)
            
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
        self.logger.debug(f"Writing file: {file_path}")
        self.logger.debug(f"Content length: {len(content)}")
        
        try:
            result = safe_write_file(file_path, content, encoding)
            if result:
                self.logger.debug("Successfully wrote file")
            else:
                self.logger.debug("File unchanged, skipped writing")
            return result
        except Exception as e:
            self.logger.error(f"Failed to write file: {str(e)}")
            raise

    def _get_relative_path(self, from_path: Path, to_path: Path) -> str:
        """Get relative path from one file to another.
        
        Args:
            from_path: Path to start from.
            to_path: Path to end at.
            
        Returns:
            Relative path from from_path to to_path.
        """
        return get_relative_path(from_path, to_path)

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
            # Get safe output path with .parsed.md extension
            output_path = get_markdown_path(file_path, "parse")
            
            # Ensure parent directories exist
            ensure_parent_dirs(output_path)
            
            # Get relative path from markdown file to original file
            rel_path = self._get_relative_path(output_path, file_path)
            
            # Generate markdown content
            markdown_content = self.markdown_writer.write_document(
                title=title,
                content=content,
                metadata=kwargs
            )
            
            # Write file
            return self._safe_write_file(output_path, markdown_content)
            
        except Exception as e:
            self.logger.error(f"Failed to write markdown file: {str(e)}")
            return False

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
            Updated metadata if successful, None otherwise
        """
        pass
    
    def supports_file(self, file_path: Path) -> bool:
        """Check if handler supports file type.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file type is supported
        """
        return file_path.suffix.lstrip('.').lower() in self.file_types 

    def _save_metadata(
        self,
        file_path: Path,
        relative_path: Path,
        metadata: DocumentMetadata
    ) -> None:
        """Save document metadata.
        
        Args:
            file_path: Original file path
            relative_path: Relative path from input directory
            metadata: Document metadata
        """
        try:
            # Get the output path for the metadata file preserving directory structure
            output_metadata_path = self.output_manager.get_output_path_for_phase(
                relative_path,
                "parse",
                ".metadata.json"
            )
            
            # Ensure parent directories exist
            output_metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            metadata.save(output_metadata_path)
            
        except Exception as e:
            error_msg = f"Failed to save metadata for {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg) 