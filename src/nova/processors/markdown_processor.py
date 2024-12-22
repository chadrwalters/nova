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
    
    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process a markdown file and its attachments.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        try:
            # Find attachments directory (same name as markdown file without .md)
            attachments_dir = input_path.parent / input_path.stem
            output_attachments_dir = output_path.parent / output_path.stem
            
            # Read and process markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process markdown content
            processed_content = self.markdown_handler.process_markdown(content, input_path)
            
            # Process attachments if they exist
            if attachments_dir.exists() and attachments_dir.is_dir():
                logger.info(f"Processing attachments directory: {attachments_dir}")
                
                # Create output attachments directory
                output_attachments_dir.mkdir(parents=True, exist_ok=True)
                
                # Track link updates
                link_updates = {}
                
                # Process each file in attachments directory
                for file_path in attachments_dir.glob('**/*'):
                    if file_path.is_file():
                        try:
                            # Get relative path to maintain directory structure
                            rel_path = file_path.relative_to(attachments_dir)
                            output_file = output_attachments_dir / rel_path
                            
                            # Create parent directories if needed
                            output_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Process based on file type
                            suffix = file_path.suffix.lower()
                            if suffix in ['.pdf']:
                                output_file = output_file.with_suffix('.md')
                                output_file = self.markdown_handler.convert_document(file_path, output_file)
                                self.summary.add_processed('pdf', file_path)
                            elif suffix in ['.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.csv']:
                                output_file = output_file.with_suffix('.md')
                                output_file = self.markdown_handler.convert_document(file_path, output_file)
                                self.summary.add_processed('office', file_path)
                            elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic']:
                                output_file = self.image_processor.process(file_path, output_file)
                                self.summary.add_processed('image', file_path)
                            else:
                                # Just copy other files
                                shutil.copy2(file_path, output_file)
                                self.summary.add_processed('other', file_path)
                            
                            # Update link if file was converted
                            if output_file.suffix != file_path.suffix:
                                old_rel = rel_path.as_posix()
                                new_rel = output_file.relative_to(output_attachments_dir).as_posix()
                                link_updates[old_rel] = new_rel
                                
                        except Exception as e:
                            logger.error(f"Failed to process attachment {file_path.name}: {e}")
                            self.summary.add_skipped('error', file_path)
                
                # Update links in markdown content if needed
                if link_updates:
                    for old_path, new_path in link_updates.items():
                        processed_content = processed_content.replace(old_path, new_path)
            
            # Write processed content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to process {input_path}: {e}")
            self.summary.add_skipped('error', input_path)
            raise ProcessingError(f"Failed to process {input_path}: {e}") from e
    
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