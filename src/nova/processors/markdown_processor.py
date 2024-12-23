"""Markdown processor for converting documents to markdown format."""

import os
import shutil
from pathlib import Path
from typing import Set, Dict, List, Optional, Any, Tuple, Union
import logging
import sys
import tempfile
import io
import warnings
import json
import csv
import xml.dom.minidom
import time
import re
from datetime import datetime
import base64
import random
from urllib.parse import unquote

from markitdown import MarkItDown
from markitdown._markitdown import FileConversionException, UnsupportedFormatException
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    SpinnerColumn
)
from PIL import Image
from PIL.ExifTags import TAGS
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from .base import BaseProcessor
from .image_processor import ImageProcessor
from .office_processor import OfficeProcessor
from .components.markdown_handlers import MarkitdownHandler, ConsolidationHandler
from ..core.state import StateManager
from ..core.config import NovaConfig, ProcessorConfig
from ..core.errors import ConfigurationError, ProcessingError, NovaError
from ..core.logging import get_logger
from ..core.task_manager import TaskManager
from ..core.openai import OpenAIClient

# Filter PyMuPDF SWIG deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type SwigPyPacked has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type SwigPyObject has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type swigvarlink has no __module__ attribute")
warnings.filterwarnings('ignore', category=DeprecationWarning, module='fitz')

try:
    import pillow_heif
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False

logger = get_logger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processes markdown and office documents."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
        # Get attachment markers from config
        consolidate_config = self.config.options.get('components', {}).get('consolidate_processor', {}).get('config', {})
        
        if not consolidate_config or "attachment_markers" not in consolidate_config:
            self.logger.error("Missing consolidate_processor configuration")
            raise ProcessingError("Missing consolidate_processor configuration")
            
        self.attachment_start = consolidate_config["attachment_markers"]["start"]
        self.attachment_end = consolidate_config["attachment_markers"]["end"]
        
        self.logger.info(f"Initialized with attachment markers: {self.attachment_start}, {self.attachment_end}")
        
        self._setup()
    
    def _setup(self) -> None:
        """Set up the markdown processor."""
        try:
            # Initialize task manager
            self.task_manager = TaskManager()
            
            # Initialize the markdown parser
            self.parser = MarkItDown()
            
            # Set up handlers
            processor_config = ProcessorConfig(
                document_conversion=True,
                image_processing=True,
                metadata_preservation=True
            )
            
            # Set up handlers using the NovaConfig instance passed to the constructor
            self.handlers = {
                'markdown': MarkitdownHandler(
                    processor_config=processor_config,
                    nova_config=self.nova_config
                ),
                'consolidation': ConsolidationHandler(
                    processor_config=processor_config,
                    nova_config=self.nova_config
                )
            }
            
            # Initialize state manager using the state_dir from NovaConfig
            self.state_manager = StateManager(self.nova_config.paths.state_dir)
            
            # Initialize OpenAI client if needed
            if self.nova_config.openai.api_key:
                self.openai_client = OpenAIClient()
                
            # Get attachment markers from config
            self.attachment_markers = self.config.options.get('components', {}).get('consolidate_processor', {}).get('config', {}).get('attachment_markers', {
                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                'end': '--==ATTACHMENT_BLOCK_END==--'
            })
            
            self.logger.info("Processor setup completed")
            self.logger.info("Initialized with attachment markers:")
            self.logger.info(f"{self.attachment_markers['start']},\n")
            self.logger.info(f"{self.attachment_markers['end']}")
            
        except Exception as e:
            raise ProcessingError(f"Failed to set up markdown processor: {str(e)}")
    
    @staticmethod
    def _extract_file_path(input_path: str) -> Optional[str]:
        """Extract actual file path from input path that might contain a data URI.
        
        Args:
            input_path: Input path that might contain a data URI
            
        Returns:
            Actual file path if found, None otherwise
        """
        # First check if it's a valid path as is
        try:
            if os.path.exists(input_path):
                return input_path
        except (OSError, ValueError):
            pass
            
        # If it contains a data URI, try to extract the path part
        if 'data:' in input_path:
            # Split at the first occurrence of 'data:'
            parts = input_path.split('data:', 1)
            base_path = parts[0].strip()
            
            # Check if the extracted path exists
            try:
                if base_path and os.path.exists(base_path):
                    return base_path
            except (OSError, ValueError):
                pass
        
        return None

    def _get_safe_path(self, original_path: str) -> str:
        """Get a safe path for a file.
        
        Args:
            original_path: Original file path
            
        Returns:
            A safe path string
        """
        # Extract the directory part (everything before the last separator)
        path_without_data = original_path.split('data:', 1)[0].strip()
        path_obj = Path(path_without_data)
        
        # Generate a safe filename
        safe_name = f"nova_temp_{hash(original_path) & 0xFFFFFFFF}.md"
        
        # Combine directory with safe name if there is a directory part
        if path_obj.parent != Path('.'):
            return str(path_obj.parent / safe_name)
        else:
            return safe_name

    def _validate_directory(self, directory: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate a directory for processing.
        
        Args:
            directory: Path to directory to validate
            
        Returns:
            Tuple containing:
            - Success flag
            - Error message if any
            - Validation info dictionary
        """
        validation_info = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_files': 0,
                'total_size': 0,
                'max_depth': 0
            }
        }
        
        try:
            # Check if directory exists
            if not directory.exists():
                validation_info['errors'].append("Directory does not exist")
                return False, "Directory does not exist", validation_info
                
            # Check if it's actually a directory
            if not directory.is_dir():
                validation_info['errors'].append("Path is not a directory")
                return False, "Path is not a directory", validation_info
                
            # Check read permissions
            if not os.access(directory, os.R_OK):
                validation_info['errors'].append("Directory is not readable")
                return False, "Directory is not readable", validation_info
                
            # Collect directory statistics
            for root, dirs, files in os.walk(directory):
                depth = len(Path(root).relative_to(directory).parts)
                validation_info['stats']['max_depth'] = max(depth, validation_info['stats']['max_depth'])
                validation_info['stats']['total_files'] += len(files)
                validation_info['stats']['total_size'] += sum(f.stat().st_size for f in Path(root).glob('*') if f.is_file())
                
            validation_info['is_valid'] = True
            return True, "", validation_info
            
        except Exception as e:
            error_msg = f"Directory validation failed: {str(e)}"
            validation_info['errors'].append(error_msg)
            return False, error_msg, validation_info

    def _ensure_directory_structure(self, source_dir: Path, target_dir: Path) -> tuple[bool, str]:
        """Ensure directory structure exists and is writable.
        
        Args:
            source_dir: Source directory path
            target_dir: Target directory path
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.logger.debug(f"Ensuring directory structure: {source_dir} -> {target_dir}")
            
            # Validate source directory
            is_valid, error = self._validate_directory(source_dir)
            if not is_valid:
                self.logger.error(f"Invalid source directory: {error}")
                return False, error
            
            # Validate target directory
            is_valid, error = self._validate_directory(target_dir)
            if not is_valid:
                self.logger.error(f"Invalid target directory: {error}")
                return False, error
            
            # Create target directory structure mirroring source
            if source_dir.is_dir():
                for item in source_dir.iterdir():
                    relative_path = item.relative_to(source_dir)
                    target_path = target_dir / relative_path
                    
                    if item.is_dir():
                        self.logger.debug(f"Creating directory: {target_path}")
                        is_valid, error = self._validate_directory(target_path)
                        if not is_valid:
                            self.logger.error(f"Failed to create directory {target_path}: {error}")
                            return False, error
            
            return True, ""
            
        except Exception as e:
            error = f"Failed to ensure directory structure: {str(e)}"
            self.logger.error(error)
            return False, error

    def _copy_directory_structure(self, source_dir: Path, target_dir: Path, preserve_timestamps: bool = True) -> tuple[bool, str]:
        """Copy directory structure while preserving metadata.
        
        Args:
            source_dir: Source directory path
            target_dir: Target directory path
            preserve_timestamps: Whether to preserve timestamps
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.logger.debug(f"Copying directory structure: {source_dir} -> {target_dir}")
            
            # First ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy directory structure
            for root, dirs, files in os.walk(source_dir):
                # Get relative path from source directory
                relative_path = Path(root).relative_to(source_dir)
                target_path = target_dir / relative_path
                
                # Create directories
                for dir_name in dirs:
                    dir_path = target_path / dir_name
                    dir_path.mkdir(parents=True, exist_ok=True)
                    
                    if preserve_timestamps:
                        source_dir_path = Path(root) / dir_name
                        shutil.copystat(source_dir_path, dir_path)
            
            return True, ""
            
        except Exception as e:
            error = f"Failed to copy directory structure: {str(e)}"
            self.logger.error(error)
            return False, error

    def _process_associated_directory(self, source_dir: Path, target_dir: Path) -> tuple[bool, str]:
        """Process an associated directory, converting files to markdown where appropriate.
        
        Args:
            source_dir: Source directory path
            target_dir: Target directory path
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.logger.debug(f"Processing associated directory: {source_dir} -> {target_dir}")
            
            # Validate source directory structure
            is_valid, error, structure_info = self._validate_directory_structure(source_dir)
            if not is_valid:
                return False, f"Invalid source directory structure: {error}"
            
            # Create base target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Track statistics
            stats = {
                'files_processed': 0,
                'files_converted': 0,
                'directories_created': 0,
                'errors': 0,
                'start_time': time.time()
            }
            
            # Create a progress tracker
            progress = self._track_directory_processing(structure_info['stats']['total_files'])
            overall_task = progress.add_task(
                description="Processing directory",
                total=structure_info['stats']['total_files'],
                status="Starting..."
            )
            
            with progress:
                # Process each file while preserving directory structure
                for source_path in source_dir.rglob('*'):
                    try:
                        # Calculate relative path to preserve structure
                        relative_path = source_path.relative_to(source_dir)
                        
                        if source_path.is_dir():
                            # Create directory in target
                            new_dir = target_dir / relative_path
                            if not new_dir.exists():
                                new_dir.mkdir(parents=True, exist_ok=True)
                                stats['directories_created'] += 1
                                self.logger.debug(f"Created directory: {new_dir}")
                            continue
                        
                        if not source_path.is_file():
                            continue
                            
                        stats['files_processed'] += 1
                        progress.update(
                            overall_task,
                            advance=0,
                            status=f"Processing: {relative_path}"
                        )
                        
                        # Determine target path based on file type
                        target_path = target_dir / relative_path
                        
                        # Ensure target directory exists
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Process based on file type
                        file_type = source_path.suffix.lower()
                        if file_type in ['.md', '.txt', '.csv', '.json']:
                            # Convert text files to markdown
                            try:
                                content = self.markdown_handler.convert_to_markdown(source_path)
                                with open(target_path, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                stats['files_converted'] += 1
                                progress.update(
                                    overall_task,
                                    advance=1,
                                    status=f"Converted: {relative_path}"
                                )
                            except Exception as e:
                                self.logger.error(f"Failed to convert {source_path}: {str(e)}")
                                stats['errors'] += 1
                                progress.update(
                                    overall_task,
                                    advance=1,
                                    status=f"Error: {str(e)}"
                                )
                        else:
                            # Copy non-text files directly
                            try:
                                shutil.copy2(source_path, target_path)
                                progress.update(
                                    overall_task,
                                    advance=1,
                                    status=f"Copied: {relative_path}"
                                )
                            except Exception as e:
                                self.logger.error(f"Failed to copy {source_path}: {str(e)}")
                                stats['errors'] += 1
                                progress.update(
                                    overall_task,
                                    advance=1,
                                    status=f"Error: {str(e)}"
                                )
                    
                    except Exception as e:
                        self.logger.error(f"Failed to process {source_path}: {str(e)}")
                        stats['errors'] += 1
                        if 'overall_task' in locals():
                            progress.update(
                                overall_task,
                                advance=1,
                                status=f"Error: {str(e)}"
                            )
            
            # Calculate timing
            elapsed_time = time.time() - stats['start_time']
            
            # Log statistics
            self.logger.info(f"Associated directory processing completed in {elapsed_time:.2f}s")
            self.logger.info("Processing statistics:")
            self.logger.info(f"  - Files processed: {stats['files_processed']}")
            self.logger.info(f"  - Files converted: {stats['files_converted']}")
            self.logger.info(f"  - Directories created: {stats['directories_created']}")
            self.logger.info(f"  - Errors encountered: {stats['errors']}")
            
            # Validate target directory structure
            is_valid, error, target_structure = self._validate_directory_structure(target_dir)
            if not is_valid:
                return False, f"Invalid target directory structure after processing: {error}"
            
            # Compare source and target structures
            if target_structure['stats']['total_files'] != structure_info['stats']['total_files']:
                return False, "File count mismatch between source and target directories"
            
            if stats['errors'] > 0:
                return False, f"Encountered {stats['errors']} errors during processing"
            
            return True, ""
            
        except Exception as e:
            error = f"Failed to process associated directory: {str(e)}"
            self.logger.error(error)
            return False, error

    def _process_attachment_blocks(self, content: str) -> str:
        """Process attachment blocks in content."""
        # Track seen attachment blocks to avoid duplicates
        seen_blocks = {}
        
        # Find all attachment blocks, handling indentation
        pattern = r'^\s*--==ATTACHMENT_BLOCK: (.*?)==--\s*(.*?)\s*--==ATTACHMENT_BLOCK_END==--'
        blocks = list(re.finditer(pattern, content, re.DOTALL | re.MULTILINE))
        
        # Process blocks in reverse order to avoid offset issues
        for match in reversed(blocks):
            filename = match.group(1).strip()
            block_content = match.group(2).strip()
            full_block = match.group(0)
            
            if filename not in seen_blocks:
                seen_blocks[filename] = {
                    'content': block_content,
                    'block': full_block,
                    'start': match.start(),
                    'end': match.end()
                }
            else:
                # Remove duplicate block
                content = content[:match.start()] + content[match.end():]
        
        return content

    def _validate_content_size(self, content: str, file_size: int) -> bool:
        """Validate content size against file size.
        
        Args:
            content: Content to validate
            file_size: Expected file size
            
        Returns:
            True if content size is valid
            
        Raises:
            ProcessingError: If content size is invalid
        """
        # Get content size in bytes
        content_size = len(content.encode('utf-8'))
        
        # Calculate size difference
        size_diff = abs(content_size - file_size)
        size_ratio = size_diff / file_size
        
        # For test files (small files), allow up to 10% difference
        # For normal files, allow up to 5% difference
        max_ratio = 0.10 if file_size < 1000 else 0.05
        
        if size_ratio > max_ratio:
            # Check if content contains binary data
            try:
                content.encode('utf-8')
            except UnicodeError:
                raise ProcessingError(
                    f"Content size mismatch: content contains binary data. "
                    f"File size is {file_size} bytes, content size is {content_size} bytes"
                )
            
            raise ProcessingError(
                f"Content size mismatch: file size is {file_size} bytes, "
                f"content size is {content_size} bytes (difference: {size_ratio:.2%})"
            )
        
        return True

    def process(self, input_file: Union[str, Path], output_file: Union[str, Path]) -> None:
        """Process markdown file.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
            
        Raises:
            ProcessingError: If processing fails
        """
        self.logger.info(f"Processing markdown file: {input_file}")
        
        try:
            # Convert paths to Path objects
            input_file = Path(input_file)
            output_file = Path(output_file)
            
            # Read input file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Validate content size
            file_size = input_file.stat().st_size
            self._validate_content_size(content, file_size)
            
            # Validate content
            is_valid, error, validation_info = self._validate_content(content, input_file)
            if not is_valid:
                raise ProcessingError(f"Content validation failed: {error}")
                
            # Process content
            processed_content = self._process_content(content, input_file)
            
            # Write output file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(processed_content)
                
            self.logger.info(f"Successfully processed file: {input_file}")
            
        except Exception as e:
            error = f"Failed to process markdown file: {str(e)}"
            self.logger.error(error)
            raise ProcessingError(error) from e

    def _validate_file_content(self, file_path: Path, requirements: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
        """Validate file content against requirements.
        
        Args:
            file_path: Path to the file to validate
            requirements: Dictionary of validation requirements
            
        Returns:
            Tuple of (is_valid, error_message, validation_info)
        """
        validation_info = {
            'size': 0,
            'lines': 0,
            'empty_lines': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check file existence
            if not file_path.exists():
                return False, "File does not exist", validation_info
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                validation_info['size'] = len(content.encode('utf-8'))
                
                # Count lines
                lines = content.splitlines()
                validation_info['lines'] = len(lines)
                validation_info['empty_lines'] = sum(1 for line in lines if not line.strip())
                
                # Check minimum lines requirement
                if 'min_lines' in requirements and validation_info['lines'] < requirements['min_lines']:
                    validation_info['errors'].append(
                        f"File has too few lines: {validation_info['lines']} < {requirements['min_lines']}"
                    )
                
                # Check empty lines ratio
                if 'max_empty_lines_ratio' in requirements:
                    empty_ratio = validation_info['empty_lines'] / validation_info['lines'] if validation_info['lines'] > 0 else 1
                    if empty_ratio > requirements['max_empty_lines_ratio']:
                        validation_info['errors'].append(
                            f"Too many empty lines: {empty_ratio:.1%} > {requirements['max_empty_lines_ratio']:.1%}"
                        )
            
            # Return validation result
            is_valid = len(validation_info['errors']) == 0
            error_message = "; ".join(validation_info['errors']) if validation_info['errors'] else ""
            return is_valid, error_message, validation_info
            
        except Exception as e:
            error = f"File content validation failed: {str(e)}"
            validation_info['errors'].append(error)
            return False, error, validation_info

    def _validate_content(self, content: str, source_file: Path) -> tuple[bool, str, dict]:
        """Validate markdown content before processing.
        
        Args:
            content: The content to validate
            source_file: Path to the source file
            
        Returns:
            Tuple of (is_valid, error_message, validation_info)
        """
        self.logger.debug("Validating content")
        
        # Initialize validation info
        validation_info = {
            'size': len(content.encode('utf-8')),
            'lines': len(content.splitlines()),
            'empty_lines': 0,
            'links': 0,
            'images': 0,
            'attachments': 0,
            'errors': [],
            'warnings': []
        }
        
        # Check for minimum content
        if not content.strip():
            return False, "Content is empty", validation_info
        
        # Count empty lines
        for line in content.splitlines():
            if not line.strip():
                validation_info['empty_lines'] += 1
        
        # Check empty lines ratio
        empty_ratio = validation_info['empty_lines'] / validation_info['lines']
        if empty_ratio > 0.5:
            validation_info['warnings'].append(
                f"High ratio of empty lines: {empty_ratio:.1%}"
            )
        
        # Count links and images
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        attachment_pattern = r'--==ATTACHMENT_BLOCK: ([^=]+)==--'
        
        validation_info['links'] = len(re.findall(link_pattern, content))
        validation_info['images'] = len(re.findall(image_pattern, content))
        validation_info['attachments'] = len(re.findall(attachment_pattern, content))
        
        # Check for unmatched attachment markers
        start_markers = len(re.findall(r'--==ATTACHMENT_BLOCK:', content))
        end_markers = len(re.findall(r'--==ATTACHMENT_BLOCK_END==--', content))
        if start_markers != end_markers:
            validation_info['errors'].append(
                f"Unmatched attachment markers: {start_markers} starts, {end_markers} ends"
            )
        
        # Check for broken links
        for match in re.finditer(link_pattern, content):
            link_text = match.group(1)
            link_url = match.group(2)
            
            # Skip external links
            if link_url.startswith(('http://', 'https://', 'data:')):
                continue
            
            # Check if local file exists
            try:
                link_path = Path(source_file.parent) / link_url
                if not link_path.exists():
                    validation_info['warnings'].append(
                        f"Broken link: {link_url}"
                    )
            except Exception as e:
                validation_info['warnings'].append(
                    f"Invalid link path {link_url}: {str(e)}"
                )
        
        # Check for broken images
        for match in re.finditer(image_pattern, content):
            alt_text = match.group(1)
            image_url = match.group(2)
            
            # Skip external images
            if image_url.startswith(('http://', 'https://', 'data:')):
                continue
            
            # Check if local file exists
            try:
                image_path = Path(source_file.parent) / image_url
                if not image_path.exists():
                    validation_info['warnings'].append(
                        f"Broken image: {image_url}"
                    )
            except Exception as e:
                validation_info['warnings'].append(
                    f"Invalid image path {image_url}: {str(e)}"
                )
        
        # Log validation results
        self.logger.info("Content validation results:")
        self.logger.info(f"  Size: {validation_info['size']} bytes")
        self.logger.info(f"  Lines: {validation_info['lines']} ({validation_info['empty_lines']} empty)")
        self.logger.info(f"  Links: {validation_info['links']}")
        self.logger.info(f"  Images: {validation_info['images']}")
        self.logger.info(f"  Attachments: {validation_info['attachments']}")
        
        if validation_info['warnings']:
            self.logger.warning("Validation warnings:")
            for warning in validation_info['warnings']:
                self.logger.warning(f"  - {warning}")
        
        if validation_info['errors']:
            error_msg = "; ".join(validation_info['errors'])
            return False, error_msg, validation_info
        
        return True, "", validation_info

    def _process_markdown(self, content: str, source_file: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            source_file: Source file path
            
        Returns:
            Processed markdown content
        """
        try:
            # Process image references first
            content = self._process_image_references(content, source_file.parent)
            
            # Finally process attachments with the decoded content
            content = self._process_attachments(content, source_file.parent, source_file.parent)
            
            # Validate the processed content
            is_valid, error, processed_info = self._validate_file_content(
                source_file,
                {
                    'min_lines': 1,
                    'max_empty_lines_ratio': 0.5,
                    'required_content': [],
                    'forbidden_content': []
                }
            )
            
            if not is_valid:
                raise ProcessingError(f"Invalid processed content: {error}")
            
            return content
            
        except Exception as e:
            raise ProcessingError(f"Failed to process markdown content: {str(e)}")

    def _process_markdown_links(self, content: str) -> str:
        """Process markdown links to ensure proper URL decoding and formatting.
        
        Args:
            content: The markdown content to process
            
        Returns:
            Processed content with properly decoded and formatted links
        """
        self.logger.debug("Processing markdown links")
        
        # Track statistics
        stats = {
            'links_processed': 0,
            'links_decoded': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Process all markdown links (both regular links and images)
        link_pattern = r'(!?\[([^\]]*)\]\(([^)]+)\))(?:\s*<!--\s*({[^}]+})\s*-->)?'
        matches = list(re.finditer(link_pattern, content))
        
        # Process matches in reverse order to preserve positions
        for match in reversed(matches):
            try:
                full_match = match.group(1)
                link_text = match.group(2)
                link_url = match.group(3)
                metadata_str = match.group(4)
                is_image = full_match.startswith('!')
                
                stats['links_processed'] += 1
                
                # Skip external links and data URIs
                if link_url.startswith(('http://', 'https://', 'data:')):
                    continue
                
                # URL decode the link
                try:
                    from urllib.parse import unquote
                    decoded_url = unquote(link_url)
                    if decoded_url != link_url:
                        self.logger.debug(f"Decoded URL from {link_url} to {decoded_url}")
                        link_url = decoded_url
                        stats['links_decoded'] += 1
                except Exception as e:
                    self.logger.warning(f"URL decoding failed for {link_url}: {str(e)}")
                    stats['errors'] += 1
                    continue
                
                # Clean up the path (remove extra slashes, normalize separators)
                try:
                    cleaned_url = str(Path(link_url))
                    if cleaned_url != link_url:
                        self.logger.debug(f"Cleaned URL from {link_url} to {cleaned_url}")
                        link_url = cleaned_url
                except Exception as e:
                    self.logger.warning(f"Path cleaning failed for {link_url}: {str(e)}")
                    continue
                
                # Parse metadata if present
                metadata = {}
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid metadata for {link_url}: {metadata_str}")
                
                # Reconstruct the link with the processed URL
                if is_image:
                    new_link = f"![{link_text}]({link_url})"
                else:
                    new_link = f"[{link_text}]({link_url})"
                
                # Add back metadata if present
                if metadata:
                    new_link += f" <!-- {json.dumps(metadata)} -->"
                
                # Replace the original link
                content = content[:match.start()] + new_link + content[match.end():]
                
            except Exception as e:
                self.logger.error(f"Error processing link: {str(e)}")
                stats['errors'] += 1
                continue
        
        # Log statistics
        duration = time.time() - stats['start_time']
        self.logger.info(
            f"Processed {stats['links_processed']} links "
            f"({stats['links_decoded']} decoded) "
            f"with {stats['errors']} errors "
            f"in {duration:.2f}s"
        )
        
        return content

    def _process_attachments(self, content: str, source_dir: Path, attachments_dir: Path) -> str:
        """Process and copy attachments to the appropriate directory while preserving paths.
        
        Args:
            content: Raw markdown content
            source_dir: Directory containing the source markdown file
            attachments_dir: Directory to store attachments
            
        Returns:
            Updated content with correct attachment paths
        """
        # Track statistics
        stats = {
            'attachments_processed': 0,
            'attachments_copied': 0,
            'images_copied': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Create required directories
        attachments_dir.mkdir(parents=True, exist_ok=True)
        images_dir = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR'))
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all markdown links and images
        link_pattern = r'(!?\[([^\]]*)\]\(([^)]+)\))(?:\s*<!--\s*({[^}]+})\s*-->)?'
        matches = list(re.finditer(link_pattern, content))
        
        # Create progress tracker for all attachments
        progress = self._track_image_processing(len(matches))
        overall_task = progress.add_task(
            description="Processing attachments",
            total=len(matches),
            status="Starting..."
        )
        
        # Process matches in reverse order to preserve positions
        with progress:
            for match in reversed(matches):
                try:
                    full_match = match.group(1)
                    link_text = match.group(2)
                    file_path = match.group(3)
                    metadata_str = match.group(4)
                    is_image = full_match.startswith('!')
                    
                    progress.update(
                        overall_task,
                        advance=0,
                        status=f"Processing {'image' if is_image else 'link'}: {file_path}"
                    )
                    stats['attachments_processed'] += 1
                    
                    # Parse metadata if present
                    metadata = {}
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid metadata for {file_path}: {metadata_str}")
                    
                    # Skip external links
                    if file_path.startswith(('http://', 'https://', 'data:')):
                        progress.update(overall_task, advance=1, status="Skipped external link")
                        continue
                    
                    # URL decode the path
                    try:
                        from urllib.parse import unquote
                        file_path = unquote(file_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to URL decode path {file_path}: {str(e)}")
                    
                    # Validate and resolve the attachment path
                    is_valid, error, source_file = self._validate_attachment_path(Path(file_path), source_dir)
                    if not is_valid:
                        self.logger.warning(f"Invalid attachment: {error}")
                        stats['errors'] += 1
                        progress.update(overall_task, advance=1, status=f"Error: {error}")
                        continue
                    
                    # Process based on file type
                    file_type = source_file.suffix.lower()
                    if file_type in ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp']:
                        # Handle image files
                        success, error, target_file = self._copy_image_to_original(
                            source_file,
                            preserve_structure=True,
                            metadata=metadata
                        )
                        if not success:
                            self.logger.error(f"Failed to copy image {source_file}: {error}")
                            stats['errors'] += 1
                            progress.update(overall_task, advance=1, status=f"Error: {error}")
                            continue
                        
                        stats['images_copied'] += 1
                        
                        # Update image reference with attachment markers
                        new_path = os.path.relpath(target_file, images_dir)
                        new_link = (
                            f"--==ATTACHMENT_BLOCK: {new_path}==--\n"
                            f"![{link_text}]({new_path})\n"
                            f"--==ATTACHMENT_BLOCK_END==--"
                        )
                        progress.update(overall_task, advance=1, status=f"Copied image: {new_path}")
                    else:
                        # Handle other attachments
                        # Preserve directory structure for non-image attachments
                        rel_path = source_file.relative_to(source_dir) if source_file.is_relative_to(source_dir) else Path(source_file.name)
                        target_dir = attachments_dir / rel_path.parent
                        
                        # Create target directory
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file to target directory
                        target_file = target_dir / source_file.name
                        try:
                            shutil.copy2(source_file, target_file)
                            self.logger.debug(f"Copied attachment: {source_file} -> {target_file}")
                            stats['attachments_copied'] += 1
                            
                            # Update link with attachment markers
                            new_path = os.path.relpath(target_file, attachments_dir)
                            # Use filename as link text if empty
                            if not link_text:
                                link_text = target_file.name
                            new_link = (
                                f"--==ATTACHMENT_BLOCK: {new_path}==--\n"
                                f"[{link_text}]({new_path})\n"
                                f"--==ATTACHMENT_BLOCK_END==--"
                            )
                            progress.update(overall_task, advance=1, status=f"Copied attachment: {target_file.name}")
                        except Exception as e:
                            self.logger.error(f"Failed to copy attachment {source_file}: {str(e)}")
                            stats['errors'] += 1
                            progress.update(overall_task, advance=1, status=f"Error: {str(e)}")
                            continue
                        
                    # Update content with new link
                    content = content[:match.start()] + new_link + content[match.end():]
                
                except Exception as e:
                    self.logger.error(f"Failed to process attachment: {str(e)}")
                    stats['errors'] += 1
                    progress.update(overall_task, advance=1, status=f"Error: {str(e)}")
            
            # Calculate timing
            elapsed_time = time.time() - stats['start_time']
            
            # Update final progress status
            progress.update(
                overall_task,
                status=(
                    f"Complete - {stats['images_copied']} images, "
                    + f"{stats['attachments_copied']} attachments in {elapsed_time:.1f}s"
                )
            )
        
        # Log statistics
        self.logger.info(f"Attachment processing completed in {elapsed_time:.1f}s")
        self.logger.info("Processing statistics:")
        self.logger.info(f"  - Attachments processed: {stats['attachments_processed']}")
        self.logger.info(f"  - Images copied: {stats['images_copied']}")
        self.logger.info(f"  - Other attachments copied: {stats['attachments_copied']}")
        self.logger.info(f"  - Errors encountered: {stats['errors']}")
        
        return content

    def _unify_attachment_markers(self, text: str, fallback_name: str) -> str:
        """
        Replace or wrap any embedded attachments, images, or objects with the standard:
          --==ATTACHMENT_BLOCK: filename==--
          ... contents ...
          --==ATTACHMENT_BLOCK_END==--
        If we cannot confidently extract a file name, we default to fallback_name plus an index.
        """
        # Track processed files to avoid duplicates
        processed_files = set()
        
        # First handle JSON-style embed comments
        # Look for lines that have <!-- {"embed":"true"} --> or <!-- {"embed":"true", "preview":"true"} -->
        pattern = r'(.*?)<!-- *({.*?"embed"\s*:\s*"true".*?}) *-->'
        matches = list(re.finditer(pattern, text))
        
        # Process matches in reverse order to not affect positions of earlier matches
        for match in reversed(matches):
            prefix = match.group(1).strip()  # Content before the comment
            json_part = match.group(2)  # The JSON comment part
            
            # Extract filename from any markdown link in the prefix
            filename_match = re.search(r'\[(.*?)\]\((.*?)\)', prefix)
            if filename_match:
                link_text = filename_match.group(1)
                filename = filename_match.group(2)
                if filename not in processed_files:
                    # Replace the entire match with attachment block
                    replacement = (f"--==ATTACHMENT_BLOCK: {filename}==--\n"
                                 f"[{link_text}]({filename})\n"
                                 f"--==ATTACHMENT_BLOCK_END==--")
                    text = text[:match.start()] + replacement + text[match.end():]
                    processed_files.add(filename)
        
        # Handle image links with no embed comment
        pattern = r'(!?\[.*?\]\(.*?\))'
        matches = list(re.finditer(pattern, text))
        for match in reversed(matches):
            link_part = match.group(1)  # The [text](file) part or ![text](file) part
            
            # Only process if it starts with ! (image) or if it's a known attachment type
            if link_part.startswith('!') or any(ext in link_part.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv']):
                # Extract filename from link
                filename_match = re.search(r'\((.*?)\)', link_part)
                if filename_match:
                    filename = filename_match.group(1)
                    if filename not in processed_files:
                        # Replace the entire match with attachment block
                        replacement = (f"--==ATTACHMENT_BLOCK: {filename}==--\n"
                                     f"{link_part}\n"
                                     f"--==ATTACHMENT_BLOCK_END==--")
                        text = text[:match.start()] + replacement + text[match.end():]
                        processed_files.add(filename)
        
        # Then handle other legacy formats
        text = text.replace("[Begin Attachment:", "--==ATTACHMENT_BLOCK: ").replace("[End Attachment]", "--==ATTACHMENT_BLOCK_END==--")
        text = text.replace("<!--attachment:", "--==ATTACHMENT_BLOCK: ").replace("<!--/attachment-->", "--==ATTACHMENT_BLOCK_END==--")
        
        # Clean up any empty lines between markers and validate marker pairs
        lines = text.split('\n')
        cleaned_lines = []
        skip_empty = False
        start_count = 0
        end_count = 0
        in_block = False
        current_block = None
        
        for line in lines:
            if '--==ATTACHMENT_BLOCK:' in line:
                # Check if we're already in a block
                if in_block:
                    # Skip nested block start
                    continue
                    
                start_count += 1
                in_block = True
                skip_empty = True
                # Extract and preserve full path
                path_match = re.search(r'--==ATTACHMENT_BLOCK:\s*(.*?)==--', line)
                if path_match:
                    full_path = path_match.group(1)
                    # Keep the full path structure
                    current_block = full_path
                    cleaned_lines.append(f"--==ATTACHMENT_BLOCK: {full_path}==--")
                else:
                    cleaned_lines.append(line)
            elif '--==ATTACHMENT_BLOCK_END==--' in line:
                if not in_block:
                    # Skip unmatched end marker
                    continue
                    
                end_count += 1
                in_block = False
                skip_empty = False
                current_block = None
                cleaned_lines.append(line)
            elif skip_empty and not line.strip():
                continue
            else:
                cleaned_lines.append(line)
        
        # Add missing end markers if needed
        while end_count < start_count:
            cleaned_lines.append("--==ATTACHMENT_BLOCK_END==--")
            end_count += 1
        
        return '\n'.join(cleaned_lines)

    def _convert_html_comments(self, content: str) -> str:
        """Convert HTML comments to attachment markers.

        Args:
            content: Markdown content with HTML comments

        Returns:
            Content with HTML comments converted to attachment markers
        """
        # Extract embedded content markers
        pattern = r'<!--\s*({[^}]+})\s*-->'
        matches = re.finditer(pattern, content)
        
        # Replace each match with attachment markers
        result = content
        for match in matches:
            try:
                metadata = json.loads(match.group(1))
                if metadata.get('embed') == 'true':
                    # Replace with attachment markers
                    start_marker = '--==ATTACHMENT_BLOCK: embedded==--'
                    end_marker = '--==ATTACHMENT_BLOCK_END==--'
                    result = result.replace(match.group(0), f'{start_marker}\n{end_marker}')
            except json.JSONDecodeError:
                # Skip non-JSON comments
                continue
        
        return result

    def _process_image_references(self, content: str, base_path: Path) -> str:
        """Validate image references in markdown content.
        
        Args:
            content: Markdown content to validate
            base_path: Base path for resolving relative paths
            
        Returns:
            Processed content with attachment markers
        """
        validation_info = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Find all image references using regex
            image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            matches = list(re.finditer(image_pattern, content))
            
            # Process matches in reverse order to preserve positions
            for match in reversed(matches):
                alt_text = match.group(1)
                image_url = match.group(2)
                
                # Skip external URLs and data URIs
                if image_url.startswith(('http://', 'https://', 'data:')):
                    continue
                    
                try:
                    # Resolve and validate local path
                    image_path = base_path / image_url
                    if not image_path.exists():
                        validation_info['warnings'].append(f"Image not found: {image_url}")
                        continue
                        
                    # Validate image format
                    is_valid, error, _ = self._validate_image_format(image_path)
                    if not is_valid:
                        validation_info['warnings'].append(f"Invalid image format: {error}")
                        continue
                    
                    # Add attachment markers
                    new_content = (
                        f"--==ATTACHMENT_BLOCK: {image_url}==--\n"
                        f"![{alt_text}]({image_url})\n"
                        f"--==ATTACHMENT_BLOCK_END==--"
                    )
                    content = content[:match.start()] + new_content + content[match.end():]
                    
                except Exception as e:
                    validation_info['warnings'].append(f"Invalid image path {image_url}: {str(e)}")
            
            return content
            
        except Exception as e:
            validation_info['errors'].append(f"Image validation failed: {str(e)}")
            validation_info['is_valid'] = False
            return content

    def _extract_base64_content(self, data_uri: str, output_path: Path) -> bool:
        """Extract and save base64 content from a data URI.
        
        Args:
            data_uri: The data URI containing base64 content
            output_path: Path where to save the extracted content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Split the data URI into header and data parts
            if ',' not in data_uri:
                self.logger.error("Invalid data URI format - missing comma separator")
                return False
                
            header, data = data_uri.split(',', 1)
            
            # Extract mime type and encoding
            if ':' not in header or ';' not in header:
                self.logger.error("Invalid data URI header format")
                return False
                
            mime_parts = header.split(':')[1].split(';')
            mime_type = mime_parts[0]
            is_base64 = len(mime_parts) > 1 and mime_parts[1] == 'base64'
            
            if not is_base64:
                self.logger.error("Data URI is not base64 encoded")
                return False
            
            # Clean up the base64 data - remove whitespace and newlines
            data = ''.join(data.split())
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Decode and save the content
            try:
                import base64
                content = base64.b64decode(data)
            except Exception as e:
                self.logger.error(f"Failed to decode base64 content: {str(e)}")
                return False
            
            # Write content with error handling
            try:
                with open(output_path, 'wb') as f:
                    f.write(content)
            except Exception as e:
                self.logger.error(f"Failed to write content to {output_path}: {str(e)}")
                # Clean up partial file if it exists
                if output_path.exists():
                    output_path.unlink()
                return False
                
            self.logger.debug(f"Successfully extracted base64 content to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process base64 content: {str(e)}")
            self.logger.error(f"Error type: {type(e)}")
            return False

    def _validate_attachment_path(self, path: Path, source_dir: Path) -> tuple[bool, str, Optional[Path]]:
        """Validate an attachment path and find the actual file.
        
        Args:
            path: Path to validate
            source_dir: Source directory for relative paths
            
        Returns:
            Tuple of (is_valid, error_message, resolved_path)
        """
        self.logger.debug(f"Validating attachment path: {path}")
        
        # Skip external links and special paths
        if str(path).startswith(('http://', 'https://', '#', '/', 'data:')):
            return False, "External or special path", None
        
        # Clean up path - handle URL encoding
        try:
            cleaned_path = Path(unquote(str(path)))
            self.logger.debug(f"Cleaned path: {cleaned_path}")
        except Exception as e:
            return False, f"Failed to decode path: {str(e)}", None
        
        # Try to find the file in possible locations
        possible_paths = [
            source_dir / cleaned_path,  # Relative to source
            source_dir / cleaned_path.name,  # Just filename in source dir
            Path(os.getenv('NOVA_INPUT_DIR', '')) / cleaned_path,  # Relative to input dir
            cleaned_path  # Absolute path
        ]
        
        self.logger.debug("Checking possible locations:")
        for possible_path in possible_paths:
            self.logger.debug(f"  - {possible_path}")
            try:
                if possible_path.exists():
                    if not possible_path.is_file():
                        continue
                    
                    # Validate file size (skip files > 100MB)
                    size = possible_path.stat().st_size
                    if size > 100 * 1024 * 1024:
                        return False, f"File too large: {size / (1024*1024):.1f}MB", None
                    
                    # Basic file permission check
                    if not os.access(possible_path, os.R_OK):
                        continue
                    
                    self.logger.debug(f"Found valid file at: {possible_path}")
                    return True, "", possible_path
            except Exception as e:
                self.logger.debug(f"Error checking {possible_path}: {str(e)}")
                continue
        
        return False, "File not found or inaccessible", None

    def _validate_directory_operations(self, dir_path: Path, operation_type: str = 'read') -> tuple[bool, str, Dict[str, int]]:
        """Validate directory operations comprehensively.
        
        Args:
            dir_path: Directory path to validate
            operation_type: Type of operation ('read', 'write', or 'both')
            
        Returns:
            Tuple of (is_valid, error_message, stats)
        """
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0,
            'max_depth': 0,
            'errors': 0
        }
        
        try:
            self.logger.debug(f"Validating directory for {operation_type} operations: {dir_path}")
            
            # Check basic directory validity
            if not dir_path.exists():
                if operation_type in ('write', 'both'):
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        self.logger.debug(f"Created directory: {dir_path}")
                    except Exception as e:
                        return False, f"Failed to create directory: {str(e)}", stats
                else:
                    return False, "Directory does not exist", stats
            
            if not dir_path.is_dir():
                return False, "Path exists but is not a directory", stats
            
            # Check permissions
            required_perms = os.R_OK
            if operation_type in ('write', 'both'):
                required_perms |= os.W_OK
            
            if not os.access(dir_path, required_perms):
                perms = 'read' if operation_type == 'read' else 'read/write'
                return False, f"Insufficient {perms} permissions", stats
            
            # Check available space for write operations
            if operation_type in ('write', 'both'):
                try:
                    total, used, free = shutil.disk_usage(dir_path)
                    if free < 100 * 1024 * 1024:  # 100MB minimum
                        return False, f"Insufficient disk space: {free / (1024*1024):.1f}MB free", stats
                except Exception as e:
                    self.logger.warning(f"Could not check disk space: {str(e)}")
            
            # Analyze directory structure
            try:
                for root, dirs, files in os.walk(dir_path):
                    # Update statistics
                    stats['total_dirs'] += len(dirs)
                    stats['total_files'] += len(files)
                    
                    # Calculate depth
                    depth = len(Path(root).relative_to(dir_path).parts)
                    stats['max_depth'] = max(
                        stats['max_depth'],
                        depth
                    )
                    
                    # Check each file
                    for file in files:
                        try:
                            file_path = Path(root) / file
                            file_stat = file_path.stat()
                            stats['total_size'] += file_stat.st_size
                            
                            # Basic file validation
                            if not os.access(file_path, os.R_OK):
                                self.logger.warning(f"File not readable: {file_path}")
                                stats['errors'] += 1
                            
                            if operation_type in ('write', 'both'):
                                parent_writable = os.access(file_path.parent, os.W_OK)
                                if not parent_writable:
                                    self.logger.warning(f"Parent directory not writable: {file_path.parent}")
                                    stats['errors'] += 1
                        except Exception as e:
                            self.logger.warning(f"Error checking file {file}: {str(e)}")
                            stats['errors'] += 1
                    
                    # Check directory permissions
                    for dir_name in dirs:
                        try:
                            dir_path = Path(root) / dir_name
                            if not os.access(dir_path, required_perms):
                                self.logger.warning(f"Insufficient permissions for directory: {dir_path}")
                                stats['errors'] += 1
                        except Exception as e:
                            self.logger.warning(f"Error checking directory {dir_name}: {str(e)}")
                            stats['errors'] += 1
                
                # Log directory statistics
                self.logger.debug(f"Directory statistics for {dir_path}:")
                self.logger.debug(f"  - Total files: {stats['total_files']}")
                self.logger.debug(f"  - Total directories: {stats['total_dirs']}")
                self.logger.debug(f"  - Total size: {stats['total_size'] / (1024*1024):.1f}MB")
                self.logger.debug(f"  - Maximum depth: {stats['max_depth']}")
                self.logger.debug(f"  - Errors encountered: {stats['errors']}")
                
                if stats['errors'] > 0:
                    return False, f"Found {stats['errors']} issues during validation", stats
                
                return True, "", stats
                
            except Exception as e:
                return False, f"Error analyzing directory structure: {str(e)}", stats
                
        except Exception as e:
            return False, f"Directory validation failed: {str(e)}", stats

    def _copy_image_to_original(self, source_path: Path, preserve_structure: bool = False, metadata: Dict[str, Any] = None) -> Path:
        """Copy image to original images directory.
        
        Args:
            source_path: Source image path
            preserve_structure: Whether to preserve directory structure
            metadata: Optional metadata to preserve
            
        Returns:
            Path to copied image
        """
        try:
            # Get the destination directory
            dest_dir = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR'))
            if not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)
                
            # Generate destination path
            if preserve_structure:
                # Preserve the directory structure relative to the source
                rel_path = source_path.relative_to(source_path.parent.parent)
                dest_path = dest_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Just use the filename
                dest_path = dest_dir / source_path.name
                
            # Copy the file if source and destination are different
            if source_path != dest_path:
                shutil.copy2(source_path, dest_path)
                
            # Save metadata if provided
            if metadata:
                metadata_dir = Path(os.getenv('NOVA_IMAGE_METADATA_DIR'))
                if not metadata_dir.exists():
                    metadata_dir.mkdir(parents=True, exist_ok=True)
                    
                metadata_path = metadata_dir / f"{dest_path.stem}.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            return dest_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to copy image to original images dir: {str(e)}")

    def _validate_image_format(self, image_path: Path) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate image format and integrity comprehensively.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message, format_info)
        """
        try:
            self.logger.debug(f"Validating image format: {image_path}")
            
            # Initialize format info
            format_info = {
                'format': None,
                'mime_type': None,
                'dimensions': None,
                'bit_depth': None,
                'color_mode': None,
                'compression': None,
                'is_animated': False,
                'frame_count': 1,
                'format_details': {},
                'warnings': []
            }
            
            # Check file existence and basic attributes
            if not image_path.exists():
                return False, "Image file does not exist", None
            
            if not image_path.is_file():
                return False, "Path exists but is not a file", None
            
            # Check file size
            file_size = image_path.stat().st_size
            if file_size == 0:
                return False, "Empty file", None
            if file_size > 100 * 1024 * 1024:  # 100MB
                return False, f"File too large: {file_size / (1024*1024):.1f}MB", None
            
            # Validate file extension
            suffix = image_path.suffix.lower()
            valid_extensions = {
                '.jpg': ['JPEG', 'image/jpeg'],
                '.jpeg': ['JPEG', 'image/jpeg'],
                '.png': ['PNG', 'image/png'],
                '.gif': ['GIF', 'image/gif'],
                '.webp': ['WEBP', 'image/webp'],
                '.heic': ['HEIC', 'image/heic']
            }
            
            if suffix not in valid_extensions:
                return False, f"Unsupported file extension: {suffix}", None
            
            # Check file header/magic bytes
            try:
                with open(image_path, 'rb') as f:
                    header = f.read(12)
                    
                # JPEG: FF D8 FF
                if header.startswith(b'\xFF\xD8\xFF'):
                    format_info['format'] = 'JPEG'
                    format_info['mime_type'] = 'image/jpeg'
                # PNG: 89 50 4E 47 0D 0A 1A 0A
                elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                    format_info['format'] = 'PNG'
                    format_info['mime_type'] = 'image/png'
                # GIF: 47 49 46 38 (GIF8)
                elif header.startswith(b'GIF8'):
                    format_info['format'] = 'GIF'
                    format_info['mime_type'] = 'image/gif'
                # WEBP: 52 49 46 46 ... 57 45 42 50 (RIFF....WEBP)
                elif header.startswith(b'RIFF') and b'WEBP' in header:
                    format_info['format'] = 'WEBP'
                    format_info['mime_type'] = 'image/webp'
                # HEIC: Check using pillow-heif if available
                elif HEIF_SUPPORT and suffix == '.heic':
                    try:
                        pillow_heif.read_heif(str(image_path))
                        format_info['format'] = 'HEIC'
                        format_info['mime_type'] = 'image/heic'
                    except Exception as e:
                        return False, f"Invalid HEIC format: {str(e)}", None
                else:
                    return False, "Unrecognized or invalid image format", None
            except Exception as e:
                return False, f"Failed to read file header: {str(e)}", None
            
            # Validate image data using PIL
            try:
                with Image.open(image_path) as img:
                    # Verify image data
                    img.verify()
                    
                    # Get basic image information
                    format_info['dimensions'] = img.size
                    format_info['color_mode'] = img.mode
                    format_info['bit_depth'] = img.bits if hasattr(img, 'bits') else None
                    
                    # Check for animation
                    try:
                        format_info['is_animated'] = getattr(img, 'is_animated', False)
                        if format_info['is_animated']:
                            format_info['frame_count'] = getattr(img, 'n_frames', 1)
                    except Exception:
                        pass
                    
                    # Get format-specific details
                    if format_info['format'] == 'JPEG':
                        # Check for progressive JPEG
                        if 'progressive' in img.info:
                            format_info['format_details']['progressive'] = True
                        # Get subsampling info
                        if 'subsampling' in img.info:
                            format_info['format_details']['subsampling'] = img.info['subsampling']
                        # Get quality estimate
                        if 'quality' in img.info:
                            format_info['format_details']['quality'] = img.info['quality']
                            
                    elif format_info['format'] == 'PNG':
                        # Check for alpha channel
                        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
                        format_info['format_details']['has_alpha'] = has_alpha
                        # Get compression level
                        if 'compression' in img.info:
                            format_info['format_details']['compression_level'] = img.info['compression']
                        # Check for palette
                        format_info['format_details']['is_palettized'] = img.mode == 'P'
                        
                    elif format_info['format'] == 'GIF':
                        # Get background color
                        if 'background' in img.info:
                            format_info['format_details']['background'] = img.info['background']
                        # Check for transparency
                        format_info['format_details']['has_transparency'] = 'transparency' in img.info
                        # Get loop info for animated GIFs
                        if format_info['is_animated']:
                            format_info['format_details']['loop'] = img.info.get('loop', 0)
                            
                    elif format_info['format'] == 'WEBP':
                        # Check for animation
                        format_info['format_details']['has_animation'] = format_info['is_animated']
                        # Check for lossless compression
                        if 'lossless' in img.info:
                            format_info['format_details']['lossless'] = img.info['lossless']
                        # Get quality
                        if 'quality' in img.info:
                            format_info['format_details']['quality'] = img.info['quality']
                    
                    # Add warnings for potential issues
                    if img.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
                        format_info['warnings'].append(f"Unusual color mode: {img.mode}")
                    
                    max_dimension = max(img.size)
                    if max_dimension < 100:
                        format_info['warnings'].append(f"Image might be too small: {img.size}")
                    elif max_dimension > 8000:
                        format_info['warnings'].append(f"Image might be too large: {img.size}")
                    
                    # Log validation results
                    self.logger.debug(f"Image format validation results for {image_path}:")
                    self.logger.debug(f"  - Format: {format_info['format']}")
                    self.logger.debug(f"  - Dimensions: {format_info['dimensions']}")
                    self.logger.debug(f"  - Color mode: {format_info['color_mode']}")
                    if format_info['warnings']:
                        for warning in format_info['warnings']:
                            self.logger.warning(f"  - Warning: {warning}")
                    
                    return True, "", format_info
                    
            except Exception as e:
                return False, f"Failed to validate image data: {str(e)}", None
            
        except Exception as e:
            return False, f"Image format validation failed: {str(e)}", None

    def _track_image_processing(self, total_images: int) -> Progress:
        """Create and configure a progress tracker for image processing.
        
        Args:
            total_images: Total number of images to process
            
        Returns:
            Configured Progress instance
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            TextColumn("[cyan]{task.fields[status]}"),
            expand=True
        )

    def _process_image(self, source_path: Path, target_dir: Path = None) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process an image through the complete workflow.
        
        Args:
            source_path: Path to the source image file
            target_dir: Optional target directory (defaults to NOVA_PROCESSED_IMAGES_DIR)
            
        Returns:
            Tuple of (success, error_message, processing_info)
        """
        try:
            self.logger.info(f"Starting image processing workflow for: {source_path}")
            
            # Initialize processing info
            processing_info = {
                'source_path': str(source_path),
                'original_size': None,
                'processed_size': None,
                'format': None,
                'conversion': None,
                'optimization': None,
                'metadata': None,
                'format_info': None,
                'errors': [],
                'warnings': [],
                'processing_time': 0
            }
            
            start_time = time.time()
            
            # Step 1: Validate source image and format
            success, error, format_info = self._validate_image_format(source_path)
            if not success:
                processing_info['errors'].append(f"Format validation failed: {error}")
                return False, error, processing_info
            
            processing_info['format_info'] = format_info
            processing_info['original_size'] = source_path.stat().st_size
            processing_info['format'] = {'original': format_info['format']}
            
            # Step 2: Extract metadata
            success, error, metadata = self._extract_image_metadata(source_path)
            if success:
                processing_info['metadata'] = metadata
            
            # Step 3: Set up target directory and path
            if target_dir is None:
                target_dir = Path(os.getenv('NOVA_PROCESSED_IMAGES_DIR', ''))
            
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / source_path.name
            
            # Step 4: Process and save the image
            try:
                image = Image.open(source_path)
                
                # Apply optimizations
                processing_info['optimization'] = {
                    'original_size': image.size,
                    'resize': False,
                    'quality': None
                }
                
                # Save with appropriate settings
                save_params = {
                    'format': format_info['format'],
                    'quality': 85,
                    'optimize': True
                }
                
                # Preserve EXIF data if available
                if metadata and 'exif' in metadata:
                    try:
                        exif_bytes = image.info.get('exif', b'')
                        if exif_bytes:
                            save_params['exif'] = exif_bytes
                    except Exception as e:
                        processing_info['warnings'].append(f"Failed to preserve EXIF: {str(e)}")
                
                # Save processed image
                image.save(target_path, **save_params)
                
                # Update processing info
                processing_info['processed_size'] = target_path.stat().st_size
                processing_info['processing_time'] = time.time() - start_time
                processing_info['processed_path'] = str(target_path)
                
                # Save processing info
                try:
                    info_dir = Path(os.getenv('NOVA_IMAGE_METADATA_DIR', ''))
                    info_dir.mkdir(parents=True, exist_ok=True)
                    info_path = info_dir / f"{target_path.stem}_processing.json"
                    
                    with open(info_path, 'w', encoding='utf-8') as f:
                        json.dump(processing_info, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    processing_info['warnings'].append(f"Failed to save processing info: {str(e)}")
                
                self.logger.info(f"Image processing completed successfully in {processing_info['processing_time']:.2f}s")
                return True, "", processing_info
                
            except Exception as e:
                error = f"Image processing failed: {str(e)}"
                processing_info['errors'].append(error)
                if target_path.exists():
                    target_path.unlink()
                return False, error, processing_info
            
        except Exception as e:
            error = f"Image processing workflow failed: {str(e)}"
            if 'processing_info' in locals():
                processing_info['errors'].append(error)
                return False, error, processing_info
            return False, error, None

    def _extract_image_metadata(self, image_path: Path) -> Dict[str, Any]:
        """Extract metadata from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image metadata
        """
        metadata = {
            'format': None,
            'mode': None,
            'size': None,
            'info': {}
        }
        
        try:
            with Image.open(image_path) as img:
                metadata.update({
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'info': {k: str(v) for k, v in img.info.items()}
                })
                
            # Add file stats
            stats = image_path.stat()
            metadata['file_stats'] = {
                'size': stats.st_size,
                'created': stats.st_ctime,
                'modified': stats.st_mtime,
                'accessed': stats.st_atime
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {image_path}: {e}")
            return metadata

    def _validate_directory_structure(self, dir_path: Path, expected_structure: Dict[str, Any] = None) -> tuple[bool, str, Dict[str, Any]]:
        """Validate directory structure.
        
        Args:
            dir_path: Path to the directory to validate
            expected_structure: Dictionary of expected files and directories
        
        Returns:
            Tuple of (is_valid, error_message, structure_info)
        """
        structure_info = {
            'path': str(dir_path),
            'contents': {
                'files': [],
                'directories': []
            },
            'errors': [],
            'warnings': []
        }
        
        try:
            # First validate the directory itself
            is_valid, error, dir_info = self._validate_directory(dir_path)
            if not is_valid:
                structure_info['errors'].append(error)
                return False, error, structure_info
            
            # Scan directory contents recursively
            for root, dirs, files in os.walk(dir_path):
                try:
                    root_path = Path(root)
                    
                    # Add directories
                    for dir_name in dirs:
                        try:
                            dir_path_obj = root_path / dir_name
                            if dir_path_obj.is_relative_to(dir_path):
                                rel_dir_path = dir_path_obj.relative_to(dir_path)
                                rel_dir_str = str(rel_dir_path)
                                if rel_dir_str not in structure_info['contents']['directories']:
                                    structure_info['contents']['directories'].append(rel_dir_str)
                        except Exception as e:
                            self.logger.warning(f"Failed to process directory {dir_name}: {str(e)}")
                        
                    # Add files
                    for file_name in files:
                        try:
                            file_path_obj = root_path / file_name
                            if file_path_obj.is_relative_to(dir_path):
                                rel_file_path = file_path_obj.relative_to(dir_path)
                                rel_file_str = str(rel_file_path)
                                if rel_file_str not in structure_info['contents']['files']:
                                    structure_info['contents']['files'].append(rel_file_str)
                        except Exception as e:
                            self.logger.warning(f"Failed to process file {file_name}: {str(e)}")
                            
                except Exception as e:
                    self.logger.warning(f"Failed to process directory {root}: {str(e)}")
                    continue
            
            # Add directory validation info
            structure_info.update({k: v for k, v in dir_info.items() if k not in ['path', 'errors', 'warnings']})
            structure_info['warnings'].extend(dir_info['warnings'])
            
            # Validate expected structure if provided
            if expected_structure:
                if 'required_dirs' in expected_structure:
                    for expected_dir in expected_structure['required_dirs']:
                        if expected_dir not in structure_info['contents']['directories']:
                            structure_info['errors'].append(f"Required directory missing: {expected_dir}")
                
                if 'required_files' in expected_structure:
                    for expected_file in expected_structure['required_files']:
                        if expected_file not in structure_info['contents']['files']:
                            structure_info['errors'].append(f"Required file missing: {expected_file}")
            
            # Calculate statistics
            structure_info['stats'] = {
                'total_files': len(structure_info['contents']['files']),
                'total_dirs': len(structure_info['contents']['directories'])
            }
            
            # Print debug info
            self.logger.debug("\nDebug - Directory Structure:")
            self.logger.debug(f"Base path: {dir_path}")
            self.logger.debug("Directories found:")
            for d in structure_info['contents']['directories']:
                self.logger.debug(f"  - {d}")
            self.logger.debug("Files found:")
            for f in structure_info['contents']['files']:
                self.logger.debug(f"  - {f}")
            
            return True, "", structure_info
            
        except Exception as e:
            error = f"Directory structure validation failed: {str(e)}"
            structure_info['errors'].append(error)
            return False, error, structure_info

    def _validate_file_presence(self, dir_path: Path, expected_files: Optional[Dict[str, Any]] = None) -> tuple[bool, str, Dict[str, Any]]:
        """Validate presence and integrity of files in a directory.
        
        Args:
            dir_path: Directory path to validate
            expected_files: Optional dictionary describing expected files and their properties
            
        Returns:
            Tuple of (is_valid, error_message, validation_info)
        """
        try:
            self.logger.info(f"Validating file presence in: {dir_path}")
            
            # Initialize validation info
            validation_info = {
                'path': str(dir_path),
                'files_checked': 0,
                'files_present': 0,
                'files_missing': 0,
                'files_invalid': 0,
                'total_size': 0,
                'present_files': [],
                'missing_files': [],
                'invalid_files': [],
                'file_types': {},
                'errors': [],
                'warnings': []
            }
            
            # First validate directory structure
            is_valid, error, structure_info = self._validate_directory_structure(dir_path)
            if not is_valid:
                validation_info['errors'].append(f"Directory structure validation failed: {error}")
                return False, error, validation_info
            
            # Track all files in directory
            all_files = set(structure_info['contents']['files'])
            validation_info['files_checked'] = len(all_files)
            validation_info['total_size'] = structure_info['stats']['total_size']
            validation_info['file_types'] = structure_info['contents']['file_types'].copy()
            
            # If expected files are provided, validate against them
            if expected_files:
                # Check required files
                if 'required_files' in expected_files:
                    for file_spec in expected_files['required_files']:
                        validation_info['files_checked'] += 1
                        
                        # Handle both string and dict specifications
                        if isinstance(file_spec, str):
                            file_path = file_spec
                            requirements = {}
                        else:
                            file_path = file_spec['path']
                            requirements = file_spec.get('requirements', {})
                        
                        # Check file presence
                        if file_path not in all_files:
                            validation_info['files_missing'] += 1
                            validation_info['missing_files'].append(file_path)
                            validation_info['errors'].append(f"Required file missing: {file_path}")
                            continue
                        
                            # Validate file against requirements
                            full_path = dir_path / file_path
                            try:
                                # Basic file checks
                                if not full_path.is_file():
                                    validation_info['files_invalid'] += 1
                                    validation_info['invalid_files'].append(file_path)
                                    validation_info['errors'].append(f"Path exists but is not a file: {file_path}")
                                    continue
                                    
                                if not os.access(full_path, os.R_OK):
                                    validation_info['files_invalid'] += 1
                                    validation_info['invalid_files'].append(file_path)
                                    validation_info['errors'].append(f"File not readable: {file_path}")
                                    continue
                                
                                # Get file stats
                                file_stat = full_path.stat()
                                
                                # Check size requirements
                                if 'min_size' in requirements and file_stat.st_size < requirements['min_size']:
                                    validation_info['files_invalid'] += 1
                                    validation_info['invalid_files'].append(file_path)
                                    validation_info['errors'].append(
                                        f"File too small: {file_path} ({file_stat.st_size} < {requirements['min_size']} bytes)"
                                    )
                                    continue
                                    
                                if 'max_size' in requirements and file_stat.st_size > requirements['max_size']:
                                    validation_info['files_invalid'] += 1
                                    validation_info['invalid_files'].append(file_path)
                                    validation_info['errors'].append(
                                        f"File too large: {file_path} ({file_stat.st_size} > {requirements['max_size']} bytes)"
                                    )
                                    continue
                                
                                # Check modification time requirements
                                if 'max_age' in requirements:
                                    age = time.time() - file_stat.st_mtime
                                    if age > requirements['max_age']:
                                        validation_info['warnings'].append(
                                            f"File might be outdated: {file_path} (age: {age/86400:.1f} days)"
                                        )
                            except Exception as e:
                                validation_info['files_invalid'] += 1
                                validation_info['invalid_files'].append(file_path)
                                validation_info['errors'].append(f"Failed to validate file {file_path}: {str(e)}")
                                continue
                                
                                # Check content requirements if specified
                                if 'content_check' in requirements:
                                    try:
                                        with open(full_path, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                            
                                            # Check for required content
                                            if 'required_content' in requirements['content_check']:
                                                for required in requirements['content_check']['required_content']:
                                                    if required not in content:
                                                        validation_info['files_invalid'] += 1
                                                        validation_info['invalid_files'].append(file_path)
                                                        validation_info['errors'].append(
                                                            f"Required content missing in file: {file_path}"
                                                        )
                                                        break
                                            
                                            # Check for forbidden content
                                            if 'forbidden_content' in requirements['content_check']:
                                                for forbidden in requirements['content_check']['forbidden_content']:
                                                    if forbidden in content:
                                                        validation_info['files_invalid'] += 1
                                                        validation_info['invalid_files'].append(file_path)
                                                        validation_info['errors'].append(
                                                            f"Forbidden content found in file: {file_path}"
                                                        )
                                                        break
                                            
                                            # Check content format if specified
                                            if 'format_check' in requirements['content_check']:
                                                format_check = requirements['content_check']['format_check']
                                                try:
                                                    if format_check == 'json':
                                                        json.loads(content)
                                                    elif format_check == 'markdown':
                                                        if not content.strip():
                                                            validation_info['files_invalid'] += 1
                                                            validation_info['invalid_files'].append(file_path)
                                                            validation_info['errors'].append(
                                                                f"Empty markdown file: {file_path}"
                                                            )
                                                            continue
                                                    
                                                    # File passed all checks
                                                    validation_info['files_present'] += 1
                                                    validation_info['present_files'].append(file_path)
                                                except (json.JSONDecodeError, Exception) as e:
                                                    validation_info['files_invalid'] += 1
                                                    validation_info['invalid_files'].append(file_path)
                                                    error_msg = "Invalid JSON format" if isinstance(e, json.JSONDecodeError) else str(e)
                                                    validation_info['errors'].append(
                                                        f"Failed to check file content: {file_path} - {error_msg}"
                                                    )
                                                    continue
                                    except Exception as e:
                                        validation_info['files_invalid'] += 1
                                        validation_info['invalid_files'].append(file_path)
                                        validation_info['errors'].append(f"Failed to read file content: {file_path} - {str(e)}")
                                        continue
                            except Exception as e:
                                validation_info['files_invalid'] += 1
                                validation_info['invalid_files'].append(file_path)
                                validation_info['errors'].append(f"Failed to validate file {file_path}: {str(e)}")
                                continue
                
                # Check file type requirements
                if 'required_file_types' in expected_files:
                    for file_type, requirements in expected_files['required_file_types'].items():
                        actual_count = validation_info['file_types'].get(file_type, 0)
                        
                        if 'min_count' in requirements and actual_count < requirements['min_count']:
                            validation_info['errors'].append(
                                f"Insufficient {file_type} files: {actual_count} < {requirements['min_count']}"
                            )
                        
                        if 'max_count' in requirements and actual_count > requirements['max_count']:
                            validation_info['errors'].append(
                                f"Too many {file_type} files: {actual_count} > {requirements['max_count']}"
                            )
            
            # Log validation results
            self.logger.info("File presence validation results:")
            self.logger.info(f"  Path: {validation_info['path']}")
            self.logger.info("  Statistics:")
            self.logger.info(f"    - Files checked: {validation_info['files_checked']}")
            self.logger.info(f"    - Files present: {validation_info['files_present']}")
            self.logger.info(f"    - Files missing: {validation_info['files_missing']}")
            self.logger.info(f"    - Files invalid: {validation_info['files_invalid']}")
            self.logger.info(f"    - Total size: {validation_info['total_size'] / (1024*1024):.1f}MB")
            
            if validation_info['errors']:
                self.logger.error("  Errors:")
                for error in validation_info['errors']:
                    self.logger.error(f"    - {error}")
            
            if validation_info['warnings']:
                self.logger.warning("  Warnings:")
                for warning in validation_info['warnings']:
                    self.logger.warning(f"    - {warning}")
            
            # Return validation result
            is_valid = len(validation_info['errors']) == 0
            error_message = "; ".join(validation_info['errors']) if validation_info['errors'] else ""
            return is_valid, error_message, validation_info
            
        except Exception as e:
            error = f"File presence validation failed: {str(e)}"
            self.logger.error(error)
            if 'validation_info' in locals():
                validation_info['errors'].append(error)
                return False, error, validation_info
            return False, error, {
                'path': str(dir_path),
                'errors': [error]
            }

    def _create_validation_log(self, validation_data: Dict[str, Any], validation_type: str) -> tuple[bool, str, Dict[str, Any]]:
        """Create a validation log from validation data.
        
        Args:
            validation_data: Dictionary containing validation results
            validation_type: Type of validation performed
            
        Returns:
            Tuple of (success, error_message, log_info)
        """
        log_info = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': validation_type,
            'success': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'details': {}
        }
        
        try:
            # Copy statistics
            for key, value in validation_data.items():
                if isinstance(value, (int, float, bool, str)):
                    log_info['stats'][key] = value
                elif isinstance(value, (list, dict)):
                    log_info['details'][key] = value
            
            # Copy errors and warnings
            if 'errors' in validation_data:
                log_info['errors'].extend(validation_data['errors'])
                log_info['success'] = len(log_info['errors']) == 0
            
            if 'warnings' in validation_data:
                log_info['warnings'].extend(validation_data['warnings'])
            
            # Save log to file
            try:
                log_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE')) / '.logs'
                log_dir.mkdir(parents=True, exist_ok=True)
                
                log_path = log_dir / f"validation_{validation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(log_info, f, indent=2, ensure_ascii=False)
            except Exception as e:
                log_info['warnings'].append(f"Failed to save validation log: {str(e)}")
            
            return log_info['success'], "", log_info
            
        except Exception as e:
            error = f"Failed to create validation log: {str(e)}"
            log_info['errors'].append(error)
            log_info['success'] = False
            return False, error, log_info

    def _track_directory_processing(self, directory: Path, success: bool = True, error: str = None) -> None:
        """Track directory processing state.
        
        Args:
            directory: Directory being processed
            success: Whether processing was successful
            error: Error message if processing failed
        """
        if not hasattr(self, '_directory_processing_state'):
            self._directory_processing_state = {}
            
        self._directory_processing_state[str(directory)] = {
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }

    def _copy_attachment(self, source: Path, dest: Path) -> bool:
        """Copy an attachment file, handling cases where source and destination are the same."""
        try:
            if source == dest:
                self.logger.debug(f"Source and destination are the same, skipping copy: {source}")
                return True
                
            if not source.exists():
                self.logger.error(f"Source file does not exist: {source}")
                return False
                
            # Create destination directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(source, dest)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy attachment {source} to {dest}: {str(e)}")
            return False

    def _process_content(self, content: str, source_file: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Content to process
            source_file: Source file path
            
        Returns:
            Processed content
        """
        # Process attachment blocks
        content = self._process_attachment_blocks(content)
        
        # Process markdown links
        content = self._process_markdown_links(content)
        
        # Process image references
        content = self._process_image_references(content, source_file.parent)
        
        return content