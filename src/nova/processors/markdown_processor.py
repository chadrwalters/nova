"""Markdown processor for converting documents to markdown format."""

import os
import shutil
from pathlib import Path
from typing import Set, Dict, List, Optional
from dataclasses import dataclass, field
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

from .image_processor import ImageProcessor
from ..core.state import StateManager
from ..core.errors import ConfigurationError

from rich.console import Console
from rich.theme import Theme

from tqdm import tqdm

from .office_processor import OfficeProcessor

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

from ..core.config import NovaConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger

logger = get_logger(__name__)

custom_theme = Theme({
    'title': 'bold blue',           # Section headers
    'path': 'cyan',                 # File paths
    'stats': 'bold cyan',           # Statistics
    'success': 'green',             # Success messages
    'warning': 'yellow',            # Warnings
    'error': 'red',                 # Errors
    'info': 'blue',                 # Info messages
    'highlight': 'magenta',         # Important numbers
    'detail': 'dim white',          # Additional details
    'cache': 'cyan',                # Cache-related info
    'progress': 'green',            # Progress indicators
    'skip': 'yellow'                # Skipped items
})

console = Console(theme=custom_theme)

def setup_openai_client() -> Optional[OpenAI]:
    """Initialize OpenAI client with proper error handling."""
    # Check both possible env var names
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_key:
        logger.warning("OpenAI API key not found in environment variable OPENAI_API_KEY")
        return None
        
    try:
        client = OpenAI(api_key=openai_key)
        
        # Test the client with a minimal request
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[{
                "role": "user",
                "content": "Test connection"
            }],
            max_tokens=1
        )
        
        logger.info("OpenAI client initialized and tested successfully")
        return client
        
    except OpenAIError as e:
        error_msg = f"OpenAI API error: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
        
    except Exception as e:
        error_msg = f"Failed to initialize OpenAI client: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

class MarkdownProcessor:
    """Processes markdown and office documents."""
    
    def __init__(self, config: NovaConfig):
        """Initialize processor with configuration."""
        self.config = config
        self.output_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))
        self.summary = ProcessingSummary()
        
        # Configure logging first
        log_level = os.getenv('NOVA_LOG_LEVEL', 'INFO').upper()
        logging.getLogger().handlers = []  # Remove all handlers from root logger
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().setLevel(log_level)
        
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
        self.md = MarkdownIt('commonmark', {'typographer': config.markdown.typographer})
        self.md.enable('table')
        self.md.enable('strikethrough')
        
        # Initialize OpenAI client with proper error handling
        try:
            openai_client = setup_openai_client()
            if openai_client:
                logger.info("OpenAI integration enabled - image descriptions will be generated")
            else:
                logger.warning("OpenAI integration disabled - image descriptions will be limited")
        except ConfigurationError as e:
            logger.error(f"OpenAI configuration error: {str(e)}")
            logger.warning("Continuing without OpenAI integration - image descriptions will be limited")
            openai_client = None
        
        # Initialize image processor
        self.image_processor = ImageProcessor(
            config=config,
            openai_client=openai_client,
            summary=self.summary
        )
        logger.debug(f"Initialized image processor: {self.image_processor}")
        
        # Initialize markdown handler with image processor
        self.markdown_handler = MarkitdownHandler(
            config=config,
            image_processor=self.image_processor,
            output_dir=self.output_dir
        )
        logger.debug(f"Initialized markdown handler with image processor: {self.markdown_handler.image_processor}")
        
        # Initialize document converter with image support
        self.converter = MarkItDown(
            llm_client=openai_client,
            llm_model="gpt-4-turbo-2024-04-09" if openai_client else None
        )
        
        self.office_processor = OfficeProcessor()
 
    def _process_markdown_file(self, input_path: Path, output_path: Path) -> None:
        """Process a markdown file."""
        try:
            # Read the markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process markdown content using the handler
            processed_content, stats = self.markdown_handler.process_markdown(content, input_path)
            
            # Write processed markdown
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            # Update summary stats
            if stats and 'images' in stats:
                self.stats.update(stats)
            
        except Exception as e:
            raise ProcessingError(f"Failed to process markdown file {input_path}: {e}")

    def process_markdown_with_attachments(self, input_path: Path, pbar: tqdm) -> None:
        """Process a markdown file and its attachments directory if it exists."""
        try:
            # Process the markdown file itself
            rel_path = input_path.relative_to(os.getenv('NOVA_INPUT_DIR'))
            output_path = self.output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read the markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process markdown content using the handler
            logger.debug(f"Processing markdown with handler: {self.markdown_handler}")
            logger.debug(f"Original content length: {len(content)}")
            logger.debug(f"Original content: {content[:200]}...")  # First 200 chars
            
            processed_content = self.markdown_handler.process_markdown(content, input_path)
            
            logger.debug(f"Processed content length: {len(processed_content)}")
            logger.debug(f"Processed content: {processed_content[:200]}...")  # First 200 chars
            
            # Write processed markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            # Process attachments directory if it exists
            input_attachments_dir = input_path.parent / input_path.stem
            if input_attachments_dir.exists() and input_attachments_dir.is_dir():
                output_attachments_dir = output_path.parent / output_path.stem
                output_attachments_dir.mkdir(parents=True, exist_ok=True)
                
                for attachment in input_attachments_dir.iterdir():
                    if attachment.is_file():
                        suffix = attachment.suffix.lower()
                        filename = attachment.name
                        
                        # Handle different file types
                        if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.HEIC'}:
                            try:
                                start_time = time.time()
                                metadata = self.image_processor.process_image(attachment, output_attachments_dir)
                                
                                # Update stats
                                self.stats['api_calls'] = self.image_processor.stats['api_calls']
                                self.stats['api_time_total'] = self.image_processor.stats['api_time_total']
                                self.stats['cache_hits'] = self.image_processor.stats['cache_hits']
                                self.stats['images_processed'] = self.image_processor.stats['images_processed']
                                
                                # Update status but don't print
                                processing_time = time.time() - start_time
                                if processing_time >= 0.1:  # Only update for non-cached images
                                    display_name = os.path.basename(metadata.processed_path)
                                    if len(display_name) > 30:
                                        display_name = display_name[:27] + "..."
                                    tqdm.write(f"Processed {display_name} ({processing_time:.1f}s)")
                                
                            except Exception as e:
                                warning = f"Could not process image {attachment.name}"
                                console.print(f"\n[warning]Warning:[/] [path]{warning}[/]")
                                console.print(f"[detail]Location:[/] [path]{rel_path}[/]")
                                console.print(f"[detail]Reason:[/] [warning]{str(e)}[/]")
                                self.summary.add_warning(f"{warning} - {str(e)}")
                                self.summary.add_skipped('error', attachment)
                
                        elif suffix in {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'}:
                            try:
                                # Use the dedicated office document processor
                                result = self._process_office_document(attachment, output_attachments_dir)
                                
                                # Save the markdown output
                                output_md = output_attachments_dir / f"{attachment.stem}.md"
                                with open(output_md, 'w', encoding='utf-8') as f:
                                    f.write(result)
                                
                                self.summary.add_processed('office', attachment)
                                
                            except Exception as e:
                                self.summary.add_warning(f"Failed to process document {attachment.name}: {e}")
                                self.summary.add_skipped('error', attachment)
                                
                        else:
                            # Copy other files directly
                            try:
                                shutil.copy2(attachment, output_attachments_dir / attachment.name)
                                self.summary.add_processed('text', attachment)
                            except Exception as e:
                                self.summary.add_warning(f"Failed to copy file {attachment.name}: {e}")
                                self.summary.add_skipped('error', attachment)
            
            self.summary.add_processed('markdown', input_path)
            
        except Exception as e:
            error = f"Failed to process markdown file {input_path.name}: {str(e)}"
            print(f"\nError: {error}")
            self.summary.add_error(error)
            self.summary.add_skipped('error', input_path)

    def process_directory(self, input_dir: Path) -> None:
        """Process all files in a directory."""
        try:
            # Track overall stats
            stats = {
                'markdown': 0,
                'office': 0,
                'text': 0,
                'skipped': 0,
                'errors': [],
                'images': {
                    'total': 0,
                    'processed': 0,
                    'with_description': 0,
                    'failed': 0,
                    'heic_converted': 0,
                    'total_original_size': 0,
                    'total_processed_size': 0,
                    'formats': {}
                }
            }
            
            # Process each file
            for file_path in self._get_input_files(input_dir):
                try:
                    # Get relative path for output
                    rel_path = file_path.relative_to(input_dir)
                    output_path = self.output_dir / rel_path
                    
                    # Create output directory
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Process based on file type
                    if self._is_markdown_file(file_path):
                        stats['markdown'] += 1
                        content = self._read_file(file_path)
                        processed_content, file_stats = self.markdown_handler.process_markdown(content, file_path)
                        if file_stats and 'images' in file_stats:
                            stats['images']['total'] += file_stats['images']['total']
                            stats['images']['processed'] += file_stats['images']['processed']
                            stats['images']['with_description'] += file_stats['images']['with_description']
                            stats['images']['failed'] += file_stats['images']['failed']
                            stats['images']['heic_converted'] += file_stats['images']['heic_converted']
                            stats['images']['total_original_size'] += file_stats['images']['total_original_size']
                            stats['images']['total_processed_size'] += file_stats['images']['total_processed_size']
                            # Update format counts
                            for fmt, count in file_stats['images'].get('formats', {}).items():
                                stats['images']['formats'][fmt] = stats['images']['formats'].get(fmt, 0) + count
                        self._write_file(output_path, processed_content)
                        
                    elif self._is_office_file(file_path):
                        stats['office'] += 1
                        content = self.markdown_handler.convert_document(file_path)
                        self._write_file(output_path.with_suffix('.md'), content)
                        
                    else:
                        stats['text'] += 1
                        content = self._read_file(file_path)
                        self._write_file(output_path, content)
                        
                except Exception as e:
                    error = f"Could not process {file_path.name} - {str(e)}"
                    stats['errors'].append(error)
                    stats['skipped'] += 1
                    logger.error(error)
                    continue
            
            # Print processing summary
            console.print("\n\n=== Processing Summary ===\n")
            
            console.print("[title]Processed files:[/]")
            console.print(f"  [stats]Markdown:[/] [highlight]{stats['markdown']}[/] files")
            console.print(f"  [stats]Office:[/] [highlight]{stats['office']}[/] files")
            console.print(f"  [stats]Text:[/] [highlight]{stats['text']}[/] files")
            
            if stats['images']['total'] > 0:
                size_reduction = ((stats['images']['total_original_size'] - stats['images']['total_processed_size']) 
                                / stats['images']['total_original_size'] * 100) if stats['images']['total_processed_size'] > 0 else 0
                
                console.print("\n[title]Image Processing:[/]")
                console.print(f"  [stats]Total Images:[/] [highlight]{stats['images']['total']}[/]")
                console.print(f"  [stats]Successfully Processed:[/] [highlight]{stats['images']['processed']}/{stats['images']['total']}[/]")
                console.print(f"  [stats]With Descriptions:[/] [highlight]{stats['images']['with_description']}[/]")
                console.print(f"  [stats]Failed:[/] [highlight]{stats['images']['failed']}[/]")
                console.print(f"  [stats]HEIC Conversions:[/] [highlight]{stats['images']['heic_converted']}[/]")
                console.print(f"  [stats]Original Size:[/] [highlight]{stats['images']['total_original_size']/1024/1024:.1f}MB[/]")
                console.print(f"  [stats]Processed Size:[/] [highlight]{stats['images']['total_processed_size']/1024/1024:.1f}MB[/]")
                console.print(f"  [stats]Size Reduction:[/] [highlight]{size_reduction:.1f}%[/]")
                
                if stats['images']['formats']:
                    console.print("\n[stats]Image Formats:[/]")
                    for fmt, count in stats['images']['formats'].items():
                        console.print(f"  • {fmt.upper()}: [highlight]{count}[/]")
            
            if stats['skipped'] > 0:
                console.print("\n[title]Skipped files:[/]")
                console.print(f"  [error]Error:[/] [highlight]{stats['skipped']}[/] files")
            
            console.print(f"\n[stats]Total files processed:[/] [highlight]{stats['markdown'] + stats['office'] + stats['text']}[/]")
            console.print(f"[stats]Total files skipped:[/] [highlight]{stats['skipped']}[/]")
            
            if stats['errors']:
                console.print("\n[error]Warnings:[/]")
                for error in stats['errors']:
                    console.print(f"  • {error}")
            
        except Exception as e:
            logger.error(f"Failed to process directory {input_dir}: {e}")
            raise
 