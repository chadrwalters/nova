"""Base handler for document processing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
import os
import shutil

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from ..cache.manager import CacheManager


class BaseHandler(ABC):
    """Base class for document handlers."""
    
    name: str
    version: str
    file_types: List[str]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.
        
        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.metadata = None
        self.cache_manager = CacheManager(config)
        self.logger = logging.getLogger(__name__)
    
    def _get_safe_path_str(self, file_path: Union[str, Path]) -> str:
        """Get safe string representation of path.
        
        Args:
            file_path: Path to convert.
            
        Returns:
            Safe string representation of path.
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
        """Safely read a file.
        
        Args:
            file_path: Path to file.
            mode: File mode ('r' for text, 'rb' for binary).
            encoding: Optional encoding for text mode.
            
        Returns:
            File contents as string or bytes.
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
            raise ValueError(f"Failed to read file {self._get_safe_path_str(file_path)}: {str(e)}") from e
            
    def _safe_write_file(self, file_path: Path, content: str) -> None:
        """Write content to file safely.
        
        Args:
            file_path: Path to write file to.
            content: Content to write.
        """
        try:
            # Create parent directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If we're in the parse directory, ensure we only write markdown files
            parse_dir = os.path.join("phases", "parse")
            if parse_dir in str(file_path):
                # Convert file path to .parsed.md if it's not already
                if not str(file_path).endswith(".parsed.md"):
                    # Remove any existing .parsed extension
                    stem = file_path.stem
                    if stem.endswith(".parsed"):
                        stem = stem[:-7]  # Remove .parsed
                    file_path = file_path.parent / (stem + ".parsed.md")
                
            # Create a temporary file in the same directory
            temp_path = file_path.parent / f"{file_path.name}.tmp"
            
            # Write content to temporary file
            with open(temp_path, "w") as f:
                f.write(content)
                
            # Use shutil.copy2 to preserve timestamps when moving to final location
            shutil.copy2(temp_path, file_path)
            
            # Clean up temporary file
            temp_path.unlink()
                
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {str(e)}")

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

    def _write_markdown(self, markdown_path: Path, title: str, file_path: Path, content: str, **kwargs) -> None:
        """Write markdown content to file.
        
        Args:
            markdown_path: Path to write markdown file to
            title: Title for markdown file
            file_path: Path to original file
            content: Processed content
            **kwargs: Additional handler-specific parameters
        """
        # Get relative path from markdown to original
        rel_path = self._get_relative_path(markdown_path, file_path)
        
        markdown_content = f"""# {title}

## Content

{content}

[Original File: {file_path.name}]({rel_path})
"""
        
        self._safe_write_file(markdown_path, markdown_content)

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
    ) -> DocumentMetadata:
        """Process a file."""
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata if not provided
        if not metadata:
            metadata = DocumentMetadata(
                file_name=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix[1:] if file_path.suffix else "",
                handler_name=self.name,
                handler_version=self.version,
                processed=True,
            )
            
        # Process file
        try:
            # Process content
            content = await self._process_content(file_path)
            metadata.metadata["text"] = content
            
            # Create output file
            output_file = output_dir / f"{file_path.stem}.parsed.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write markdown file
            self._write_markdown(output_file, file_path.stem, file_path, content)
            
            # Add output file to metadata
            metadata.metadata.setdefault("output_files", []).append(str(output_file))
            metadata.processed = True
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            metadata.errors.append({
                "phase": self.name,
                "message": str(e)
            })
            metadata.processed = False
            return metadata
    
    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Output directory.
            metadata: Document metadata.
                
        Returns:
            Document metadata, or None if file is ignored.
            
        This is the default implementation that most handlers can use.
        Override this method only if you need special processing.
        """
        try:
            # Create markdown file path
            markdown_path = output_dir / f"{file_path.stem}.parsed.md"
            
            # Process content
            content = await self._process_content(file_path)
            
            # Write markdown file
            self._write_markdown(markdown_path, file_path.stem, file_path, content)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['content_length'] = len(content)
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {str(e)}")
            metadata.add_error(self.name, str(e))
            return metadata
    
    def supports_file(self, file_path: Union[str, Path]) -> bool:
        """Check if handler supports file.
        
        Args:
            file_path: Path to file.
            
        Returns:
            True if handler supports file, False otherwise.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        return file_path.suffix.lstrip('.').lower() in self.file_types 