"""Markdown processor for converting documents to markdown format."""

import os
import shutil
from pathlib import Path
from typing import Set, Dict, List
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
from openai import OpenAI

from .image_processor import ImageProcessor
from ..core.state import StateManager

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

@dataclass
class ProcessingSummary:
    """Tracks processing statistics."""
    processed_files: Dict[str, List[Path]] = field(default_factory=lambda: {
        'markdown': [],
        'pdf': [],
        'office': [],
        'image': [],
        'image_cached': [],
        'other': [],
        'text': []
    })
    skipped_files: Dict[str, List[Path]] = field(default_factory=lambda: {
        'unchanged': [],
        'legacy_format': [],
        'unsupported_format': [],
        'error': []
    })
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_processed(self, file_type: str, path: Path) -> None:
        """Add a successfully processed file."""
        self.processed_files[file_type].append(path)

    def add_skipped(self, reason: str, path: Path) -> None:
        """Add a skipped file."""
        self.skipped_files[reason].append(path)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def display(self) -> None:
        """Display processing summary."""
        console.print("\n[bold blue]=== Processing Summary ===[/]")
        
        # Processed files
        if any(files for files in self.processed_files.values()):
            console.print("\n[bold]Processed files:[/]")
            for file_type, files in self.processed_files.items():
                if files:
                    if file_type == 'image':
                        cached_count = len(self.processed_files['image_cached'])
                        fresh_count = len(files)
                        if fresh_count or cached_count:
                            console.print(f"  [green]Images: {fresh_count + cached_count} total[/]")
                            console.print(f"    [green]- Freshly processed: {fresh_count}[/]")
                            console.print(f"    [cyan]- From cache: {cached_count}[/]")
                    elif file_type != 'image_cached':
                        console.print(f"  [green]{file_type.title()}: {len(files)} files[/]")

        # Skipped files
        if any(files for files in self.skipped_files.values()):
            console.print("\n[bold yellow]Skipped files:[/]")
            for reason, files in self.skipped_files.items():
                if files:
                    console.print(f"  [yellow]{reason.replace('_', ' ').title()}: {len(files)} files[/]")

        # Total summary
        total_processed = sum(len(files) for files in self.processed_files.values())
        total_skipped = sum(len(files) for files in self.skipped_files.values())
        console.print(f"\n[bold green]Total files processed: {total_processed}[/]")
        console.print(f"[bold yellow]Total files skipped: {total_skipped}[/]")

        # Show warnings and errors if any
        if self.warnings:
            console.print("\n[bold yellow]Warnings:[/]")
            for warning in self.warnings:
                console.print(f"  [yellow]• {warning}[/]")

        if self.errors:
            console.print("\n[bold red]Errors:[/]")
            for error in self.errors:
                console.print(f"  [red]• {error}[/]")

class MarkdownProcessor:
    """Processes markdown and office documents."""

    def __init__(self, config: NovaConfig):
        """Initialize processor with configuration."""
        self.config = config
        self.output_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))
        self.summary = ProcessingSummary()
        
        # Initialize state manager
        self.state_manager = StateManager(self.output_dir)
        
        # Add processing statistics
        self.stats = {
            'api_calls': 0,
            'api_time_total': 0.0,
            'cache_hits': 0,
            'images_processed': 0
        }
        
        # Initialize markdown parser
        self.md = MarkdownIt('commonmark', {'typographer': config.markdown.typographer})
        self.md.enable('table')
        self.md.enable('strikethrough')
        
        # Initialize OpenAI client if API key is available
        openai_key = os.getenv('OPEN_AI_KEY')
        logger.info("OpenAI key found: %s", bool(openai_key))
        openai_client = None
        if openai_key:
            try:
                openai_client = OpenAI(api_key=openai_key)
                # Test with the new consolidated model
                response = openai_client.chat.completions.create(
                    model="gpt-4-turbo-2024-04-09",  # Changed to new model
                    messages=[{
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text": "Test"
                        }]
                    }],
                    max_tokens=1
                )
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning("OpenAI model not available: %s", str(e))
                openai_client = None
        else:
            logger.warning("OpenAI API key not found. Image descriptions will be limited.")
        
        # Initialize image processor
        self.image_processor = ImageProcessor(config, openai_client)
        
        # Initialize document converter with image support
        self.converter = MarkItDown(
            llm_client=openai_client,
            llm_model="gpt-4-turbo-2024-04-09" if openai_client else None
        )
        
        # Configure logging to be minimal and clean
        logging.getLogger().handlers = []  # Remove all handlers from root logger
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # Configure our logger
        logger.handlers = []  # Remove all handlers
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)

        # Suppress OpenAI HTTP request logs
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.WARNING)
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)

        self.office_processor = OfficeProcessor()

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding by trying common encodings."""
        # List of encodings to try, in order of likelihood
        encodings = [
            'utf-8',
            'utf-8-sig',  # UTF-8 with BOM
            'cp1252',     # Windows Western Europe
            'iso-8859-1', # Latin-1
            'ascii',      # ASCII
            'utf-16',     # UTF-16 with BOM
            'utf-16le',   # UTF-16 Little Endian
            'utf-16be',   # UTF-16 Big Endian
            'cp437',      # DOS/IBM
            'mac_roman'   # Old Mac encoding
        ]
        
        # Try each encoding
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Try to read the first few lines to verify encoding
                    f.read(1024)
                    f.seek(0)
                return encoding
            except UnicodeDecodeError:
                continue
            except Exception:
                continue
        
        raise FileConversionException(f"Could not detect encoding for file: {file_path.name}")

    def _convert_text_file_to_markdown(self, file_path: Path) -> str:
        """Convert text-based files (HTML, CSV, JSON, TXT, XML) to markdown."""
        suffix = file_path.suffix.lower()
        
        try:
            # First detect the encoding
            encoding = self._detect_encoding(file_path)
            
            # Read the file with detected encoding
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            if suffix == '.json':
                # Parse and pretty print JSON
                try:
                    parsed = json.loads(content)
                    formatted = json.dumps(parsed, indent=2)
                    return f"```json\n{formatted}\n```\n\n*File encoding: {encoding}*"
                except json.JSONDecodeError as e:
                    raise FileConversionException(f"Invalid JSON: {str(e)}")

            elif suffix == '.csv':
                # Convert CSV to markdown table
                try:
                    reader = csv.reader(content.splitlines())
                    rows = list(reader)
                    if not rows:
                        return f"*Empty CSV file*\n\n*File encoding: {encoding}*"
                    
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
                        md_table.append("| " + " | ".join(row) + " |")
                    
                    return "\n".join(md_table) + f"\n\n*File encoding: {encoding}*"
                except csv.Error as e:
                    raise FileConversionException(f"CSV parsing error: {str(e)}")

            elif suffix == '.xml':
                # Pretty print XML with syntax highlighting
                try:
                    parsed = xml.dom.minidom.parseString(content)
                    formatted = parsed.toprettyxml(indent="  ")
                    return f"```xml\n{formatted}\n```\n\n*File encoding: {encoding}*"
                except Exception as e:
                    raise FileConversionException(f"XML parsing error: {str(e)}")

            elif suffix == '.html':
                # Convert HTML to markdown-style code block
                # First, pretty print the HTML
                try:
                    parsed = xml.dom.minidom.parseString(content)
                    formatted = parsed.toprettyxml(indent="  ")
                    return f"```html\n{formatted}\n```\n\n*File encoding: {encoding}*"
                except Exception:
                    # If parsing fails, just format as-is
                    return f"```html\n{content}\n```\n\n*File encoding: {encoding}*"

            elif suffix == '.txt':
                # Preserve plain text formatting
                return content.strip() + f"\n\n*File encoding: {encoding}*"

            else:
                raise FileConversionException(f"Unsupported text file format: {suffix}")

        except UnicodeDecodeError:
            raise FileConversionException("Could not decode file with any supported encoding")
        except Exception as e:
            raise FileConversionException(f"Error processing file: {str(e)}")

    def process_directory(self, input_dir: Path) -> None:
        """Process all files in a directory."""
        # Header
        console.rule("[bold blue]Phase 1: Markdown Parse[/]")
        console.print(f"\nProcessing Directory: [cyan]{input_dir}[/]")
        console.print("[blue]Starting Markdown Parse Phase...[/]\n")
        
        markdown_files = []
        attachment_dirs = set()
        for file_path in input_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in {'.md', '.markdown'}:
                markdown_files.append(file_path)
                attachment_dir = file_path.parent / file_path.stem
                if attachment_dir.is_dir():
                    attachment_dirs.add(attachment_dir)
        
        with tqdm(total=len(markdown_files), 
                 desc="Processing", 
                 ncols=100,
                 bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}',
                 dynamic_ncols=True) as pbar:
            for file_path in markdown_files:
                if self.stats['api_calls'] > 0:
                    avg_time = self.stats['api_time_total'] / self.stats['api_calls']
                    pbar.set_postfix_str(f"API: {self.stats['api_calls']} calls ({avg_time:.1f}s)")
                
                if self.state_manager.needs_processing(file_path):
                    filename = file_path.name[:37] + "..." if len(file_path.name) > 40 else file_path.name
                    pbar.set_description(f"Processing {filename}")
                    try:
                        self.process_markdown_with_attachments(file_path, pbar)
                        self.state_manager.update_state(file_path)
                    except Exception as e:
                        error = f"Failed to process {file_path.name}: {str(e)}"
                        tqdm.write(f"\n[red]Error:[/] {error}")
                        self.summary.add_error(error)
                        self.summary.add_skipped('error', file_path)
                else:
                    filename = file_path.name[:37] + "..." if len(file_path.name) > 40 else file_path.name
                    pbar.set_description(f"Skipping {filename}")
                    self.summary.add_skipped('unchanged', file_path)
                pbar.update(1)
        
        # Add spacing before summary
        console.print("\n")
        self.summary.display()

    def process_file(self, input_path: Path, progress: tqdm) -> None:
        """Process a single file."""
        try:
            logger.debug(f"Processing file: {input_path}")
            
            # Determine output path
            rel_path = input_path.relative_to(os.getenv('NOVA_INPUT_DIR'))
            output_path = self.output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Process based on file type
            suffix = input_path.suffix.lower()
            if suffix in ['.md', '.markdown']:
                self._process_markdown_file(input_path, output_path)
                self.summary.add_processed('markdown', input_path)
                progress.set_description(f"Processing markdown: {input_path.name}")
            else:
                # Use MarkItDown for all other supported files
                try:
                    result = self.converter.convert(
                        str(input_path),
                        image_dir=str(output_path.parent)
                    )
                    
                    # Convert result to string if needed
                    if not isinstance(result, str):
                        if hasattr(result, 'markdown'):
                            result = result.markdown
                        elif hasattr(result, 'text'):
                            result = result.text
                        else:
                            result = str(result)
                    
                    # Write the markdown output
                    output_md = output_path.with_suffix('.md')
                    with open(output_md, 'w', encoding='utf-8') as f:
                        f.write(result)
                    
                    # Determine file type for summary
                    if suffix == '.pdf':
                        self.summary.add_processed('pdf', input_path)
                        progress.set_description(f"Processing PDF: {input_path.name}")
                    elif suffix in ['.docx', '.pptx', '.xlsx']:
                        self.summary.add_processed('office', input_path)
                        progress.set_description(f"Processing office file: {input_path.name}")
                    elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.HEIC']:
                        self.summary.add_processed('image', input_path)
                        progress.set_description(f"Processing image: {input_path.name}")
                    else:
                        self.summary.add_processed('other', input_path)
                        progress.set_description(f"Processing file: {input_path.name}")
                except Exception as e:
                    warning = f"Could not process file {input_path.name}: {str(e)}"
                    print(f"\nWarning: {warning}")
                    self.summary.add_warning(warning)
                    self.summary.add_skipped('error', input_path)
                    progress.set_description(f"Skipped file: {input_path.name}")
            
            progress.update(1)
            logger.debug(f"Processed file saved to: {output_path}")
            
        except Exception as e:
            error = f"Failed to process {input_path.name}: {str(e)}"
            print(f"\nError: {error}")
            logger.error(error)
            self.summary.add_error(error)
            self.summary.add_skipped('error', input_path)
            progress.update(1)
            # Don't raise the error, just continue with the next file

    def _convert_heic_to_jpg(self, heic_path: Path) -> Path:
        """Convert HEIC image to JPG format."""
        if not HEIF_SUPPORT:
            raise ImportError("pillow-heif is required for HEIC support. Install with: pip install pillow-heif")
            
        # Create temp file with same name but .jpg extension
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            # Read HEIC file
            heif_file = pillow_heif.read_heif(str(heic_path))
            image = heif_file.to_pillow()
            
            # Save as JPG
            image.save(tmp_path, 'JPEG', quality=95)
            
            return tmp_path
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise FileConversionException(f"Failed to convert HEIC file: {str(e)}")

    def _convert_webp_to_jpg(self, webp_path: Path) -> Path:
        """Convert WebP image to JPG format."""
        # Create temp file with same name but .jpg extension
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            # Open WebP with Pillow
            with Image.open(webp_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPG
                img.save(tmp_path, 'JPEG', quality=95)
            
            return tmp_path
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise e

    def _convert_pdf_to_markdown(self, pdf_path: Path) -> str:
        """Convert PDF to markdown using PyMuPDF."""
        if not PYMUPDF_SUPPORT:
            raise ImportError("PyMuPDF is required for PDF support. Install with: pip install pymupdf")
        
        try:
            # Open PDF
            doc = fitz.open(pdf_path)
            
            # Extract text and format as markdown
            markdown_content = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text blocks
                blocks = page.get_text("blocks")
                for block in blocks:
                    text = block[4].strip()
                    if text:
                        # Basic formatting - you can enhance this
                        if len(text) < 80 and text.isupper():
                            markdown_content.append(f"## {text}\n")
                        else:
                            markdown_content.append(f"{text}\n\n")
            
            return "\n".join(markdown_content)
        except Exception as e:
            raise FileConversionException(f"Failed to convert PDF: {str(e)}")

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
            
            # Parse and validate markdown
            self.md.parse(content)
            
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
                                start_time = time.time()  # Add start_time here
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
                                
                                # Update markdown content to reference both the image and its description
                                dir_name = input_path.stem
                                processed_images_dir = Path(os.getenv('NOVA_PROCESSED_IMAGES_DIR'))
                                image_path = f"../../{processed_images_dir.name}/{os.path.basename(metadata.processed_path)}"
                                desc_path = f"{dir_name}/{attachment.stem}.md"
                                
                                # Build reference patterns
                                filename_encoded = filename.replace('(', '%28').replace(')', '%29').replace(' ', '%20')
                                dir_encoded = input_path.stem.replace(' ', '%20')
                                old_ref_patterns = [
                                    f'![{filename}]({dir_encoded}/{filename_encoded})<!-- {{"embed":"true"}} -->',
                                    f'![{filename}]({input_path.stem}/{filename_encoded})<!-- {{"embed":"true"}} -->',
                                    f'![{filename}]({input_path.stem}/{filename})<!-- {{"embed":"true"}} -->',
                                    f'![{filename}]({dir_encoded}/{filename_encoded})',
                                    f'![{filename}]({input_path.stem}/{filename_encoded})',
                                    f'![{filename}]({input_path.stem}/{filename})',
                                    f'({input_path.stem}/{filename})'
                                ]
                                
                                # Create the new reference
                                new_ref = f'![{filename}]({image_path})<!-- {{"embed":"true"}} -->'
                                if metadata.description:
                                    new_ref += f'\n\n[Image Description]({desc_path})<!-- {{"embed":"true"}} -->'
                                
                                # Replace all old references with the new one
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, new_ref)
                                
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
                    
                        elif suffix in {'.txt', '.csv', '.json', '.html', '.xml'}:
                            try:
                                # Convert text-based files
                                result = self._convert_text_file_to_markdown(attachment)
                                
                                # Save the markdown output
                                output_md = output_attachments_dir / f"{attachment.stem}.md"
                                with open(output_md, 'w', encoding='utf-8') as f:
                                    f.write(result)
                                
                                self.summary.add_processed('text', attachment)
                                
                            except Exception as e:
                                self.summary.add_warning(f"Failed to process text file {attachment.name}: {e}")
                    
                        else:
                            self.summary.add_skipped('unsupported_format', attachment)
                            logger.warning(f"Skipping unsupported file format: {attachment.name}")
            
            # Write the processed markdown with updated references
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.summary.add_processed('markdown', input_path)
            
        except Exception as e:
            error = f"Failed to process markdown file {input_path.name}: {str(e)}"
            print(f"\nError: {error}")
            self.summary.add_error(error)
            self.summary.add_skipped('error', input_path)

    def _process_markdown_file(self, input_path: Path, output_path: Path) -> None:
        """Process a markdown file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse and validate markdown
        self.md.parse(content)
        
        # Create attachments directory if needed
        attachments_dir = output_path.parent / output_path.stem
        attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # Write processed markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def process(self, markdown_path: Path) -> Dict:
        """Process a markdown file."""
        try:
            # ... existing code ...

            # Update image references in markdown content
            content = markdown_path.read_text(encoding='utf-8')
            updated_content = content

            # Find and update HEIC image references
            for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+\.heic)\)', content, re.IGNORECASE):
                alt_text, heic_path = match.groups()
                jpg_path = heic_path[:-5] + '.jpg'  # Replace .heic with .jpg
                updated_content = updated_content.replace(
                    f'![{alt_text}]({heic_path})',
                    f'![{alt_text}]({jpg_path})'
                )

            # Write updated content if changes were made
            if content != updated_content:
                markdown_path.write_text(updated_content, encoding='utf-8')
                logger.info("Updated HEIC references in markdown", extra={
                    'file': str(markdown_path)
                })

            # ... rest of existing code ...

        except Exception as e:
            logger.error(f"Failed to process markdown {markdown_path}: {e}")
            raise ProcessingError(f"Failed to process {markdown_path.name}: {str(e)}")

    def _process_office_document(self, attachment: Path, output_dir: Path) -> str:
        """Process an office document using the dedicated processor."""
        try:
            return self.office_processor.process_document(attachment, output_dir)
        except Exception as e:
            logger.error(f"Failed to process office document {attachment.name}: {e}")
            return (
                f"# Processing Error: {attachment.name}\n\n"
                f"Failed to process document. Error: {str(e)}\n\n"
                f"## Document Information\n"
                f"- File: {attachment.name}\n"
                f"- Type: {attachment.suffix[1:].upper()}\n"
                f"- Size: {attachment.stat().st_size / 1024:.1f} KB"
            )
        