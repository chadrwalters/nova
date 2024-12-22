"""Markdown processor for converting documents to markdown format."""

import os
import shutil
from pathlib import Path
from typing import Set, Dict, List, Optional
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

from markdown_it import MarkdownIt
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
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from .base import BaseProcessor
from .image_processor import ImageProcessor
from .office_processor import OfficeProcessor
from .components.markdown_handlers import MarkitdownHandler
from ..core.state import StateManager
from ..core.config import NovaConfig, ProcessorConfig
from ..core.errors import ConfigurationError, ProcessingError, NovaError
from ..core.logging import get_logger
from ..core.openai import setup_openai_client
from ..core.summary import ProcessingSummary

# Filter PyMuPDF SWIG deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type SwigPyPacked has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type SwigPyObject has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="builtin type swigvarlink has no __module__ attribute")

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
        self._setup()
    
    def _setup(self) -> None:
        """Setup markdown processor requirements."""
        self.output_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))
        self.summary = ProcessingSummary()
        
        # Configure logging
        log_level = os.getenv('NOVA_LOG_LEVEL', 'INFO').upper()
        root_logger = logging.getLogger()
        
        # Close and remove existing handlers
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # Add new console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        root_logger.addHandler(console_handler)
        root_logger.setLevel(log_level)
        
        # Configure our logger
        logger.handlers = []  # Remove all handlers
        logger.addHandler(console_handler)
        logger.setLevel(log_level)
        
        # Suppress OpenAI HTTP request logs
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.WARNING)
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        
        logger.debug("Initializing MarkdownProcessor with log level: %s", log_level)
        
        # Initialize state manager
        self.state_manager = StateManager(self.output_dir)
        
        # Add processing statistics
        self.stats = {
            'api_calls': 0,
            'api_time_total': 0.0,
            'cache_hits': 0,
            'images_processed': 0,
            'images_with_descriptions': 0,
            'images_failed': 0
        }
        
        # Initialize markdown parser
        self.md = MarkdownIt('commonmark', {'typographer': self.nova_config.processors['markdown'].typographer})
        self.md.enable('table')
        self.md.enable('strikethrough')
        
        # Initialize OpenAI client with proper error handling
        try:
            self.openai_client = setup_openai_client()
            if self.openai_client:
                logger.info("OpenAI integration enabled - image descriptions will be generated")
            else:
                logger.warning("OpenAI integration disabled - image descriptions will be limited")
        except NovaError as e:
            logger.error(f"OpenAI configuration error: {str(e)}")
            logger.warning("Continuing without OpenAI integration - image descriptions will be limited")
            self.openai_client = None
        
        # Initialize image processor
        self.image_processor = ImageProcessor(
            processor_config=self.nova_config.processors['image'],
            nova_config=self.nova_config
        )
        logger.debug(f"Initialized image processor: {self.image_processor}")
        
        # Initialize markdown handler with image processor
        self.markdown_handler = MarkitdownHandler(
            processor_config=self.nova_config.processors['markdown'],
            nova_config=self.nova_config,
            image_processor=self.image_processor
        )
        logger.debug(f"Initialized markdown handler with image processor: {self.markdown_handler.image_processor}")
        
        # Initialize document converter with image support
        self.converter = MarkItDown(
            llm_client=self.openai_client,
            llm_model="gpt-4-turbo-2024-04-09" if self.openai_client else None
        )
        
        # Initialize office processor
        self.office_processor = OfficeProcessor(
            processor_config=self.nova_config.processors['office'],
            nova_config=self.nova_config
        )
    
    def process(self, input_file: Path, output_file: Path) -> None:
        """Process a markdown file.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
        """
        try:
            # If the file is a binary file (image, office doc, etc.), move it to the appropriate processing directory
            if self._is_binary_file(input_file):
                self._handle_binary_file(input_file)
                return
                
            # Process markdown file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Process the markdown content
            processed_content = self._process_markdown(content)
            
            # Write the processed content
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(processed_content)
                
        except Exception as e:
            logger.error(f"Failed to process {input_file}: {e}")
            raise
            
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file is binary, False otherwise
        """
        # Common binary file extensions
        binary_extensions = {
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.webp',
            # Office documents
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf',
            # Other
            '.zip', '.rar', '.7z', '.tar', '.gz'
        }
        return file_path.suffix.lower() in binary_extensions
        
    def _handle_binary_file(self, file_path: Path) -> None:
        """Handle a binary file by moving it to the appropriate processing directory.
        
        Args:
            file_path: Path to the binary file
        """
        # Determine the appropriate directory based on file type
        suffix = file_path.suffix.lower()
        
        if suffix in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.webp'}:
            # Image files go to images/original
            target_dir = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR'))
        elif suffix in {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf'}:
            # Office documents go to office/assets
            target_dir = Path(os.getenv('NOVA_OFFICE_ASSETS_DIR'))
        else:
            # Other binary files are not processed
            logger.warning(f"Skipping unsupported binary file: {file_path}")
            return
            
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the file to the appropriate directory
        target_path = target_dir / file_path.name
        shutil.copy2(file_path, target_path)
        logger.info(f"Moved binary file {file_path} to {target_path}")
        
    def _process_markdown(self, content: str) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            
        Returns:
            str: Processed markdown content
        """
        # TODO: Implement markdown processing
        return content
    
    def _process_pdf(self, input_path: Path, output_path: Path) -> Path:
        """Process a PDF file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        # Convert PDF to markdown using markitdown
        md_output = output_path.with_suffix('.md')
        content = self.markdown_handler.convert_document(input_path)
        
        # Create output directory if needed
        md_output.parent.mkdir(parents=True, exist_ok=True)
        
        # Write markdown output
        with open(md_output, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return md_output
    
    def _process_office_doc(self, input_path: Path, output_path: Path) -> Path:
        """Process an office document.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        # Convert office doc to markdown using markitdown
        md_output = output_path.with_suffix('.md')
        
        # Create output directory if needed
        md_output.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle CSV files differently
        if input_path.suffix.lower() == '.csv':
            try:
                # First detect the encoding
                encoding = self._detect_encoding(input_path)
                
                # Read the file with detected encoding
                with open(input_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                # Convert CSV to markdown table
                reader = csv.reader(content.splitlines())
                rows = list(reader)
                if not rows:
                    result = f"*Empty CSV file*\n\n*File encoding: {encoding}*"
                else:
                    # Create markdown table
                    md_table = []
                    # Header
                    md_table.append("| " + " | ".join(rows[0]) + " |")
                    # Separator
                    md_table.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
                    # Data rows
                    for row in rows[1:]:
                        # Ensure row has same number of columns as header
                        while len(row) < len(rows[0]):
                            row.append("")
                        # Escape any pipe characters in cells
                        escaped_row = [cell.replace('|', '\\|') for cell in row]
                        md_table.append("| " + " | ".join(escaped_row) + " |")
                    
                    result = f"# {input_path.stem}\n\n" + "\n".join(md_table) + f"\n\n*File encoding: {encoding}*"
                
                # Write markdown output
                with open(md_output, 'w', encoding='utf-8') as f:
                    f.write(result)
                
                logger.info(f"Successfully converted CSV file: {input_path}")
                
            except Exception as e:
                logger.error(f"Failed to convert CSV file {input_path}: {e}")
                raise
        else:
            # Convert other office docs using markitdown
            content = self.markdown_handler.convert_document(input_path)
            
            # Write markdown output
            with open(md_output, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return md_output
    
    def _process_image(self, input_path: Path, output_path: Path) -> Path:
        """Process an image file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        # Process image using image processor
        return self.image_processor.process(input_path, output_path)
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        import chardet
        
        # Read raw bytes
        with open(file_path, 'rb') as f:
            raw = f.read()
        
        # Detect encoding
        result = chardet.detect(raw)
        encoding = result['encoding']
        
        # Default to UTF-8 if detection fails
        if not encoding:
            encoding = 'utf-8'
        
        return encoding