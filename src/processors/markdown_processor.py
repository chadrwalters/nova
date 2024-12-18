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
from html.parser import HTMLParser
import html

from markdown_it import MarkdownIt
from markitdown import MarkItDown
from markitdown._markitdown import FileConversionException, UnsupportedFormatException
from tqdm import tqdm
from PIL import Image

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

@dataclass
class ProcessingSummary:
    """Tracks processing statistics."""
    processed_files: Dict[str, List[Path]] = field(default_factory=lambda: {
        'markdown': [],
        'pdf': [],
        'office': [],
        'image': [],
        'other': [],
        'text': []
    })
    skipped_files: Dict[str, List[Path]] = field(default_factory=lambda: {
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
        print("\n=== Processing Summary ===")
        
        # Processed files
        print("\nSuccessfully processed files:")
        for file_type, files in self.processed_files.items():
            if files:
                print(f"  {file_type.title()}: {len(files)} files")

        # Skipped files
        if any(files for files in self.skipped_files.values()):
            print("\nSkipped files:")
            for reason, files in self.skipped_files.items():
                if files:
                    print(f"  {reason.replace('_', ' ').title()}: {len(files)} files")

        # Total summary
        total_processed = sum(len(files) for files in self.processed_files.values())
        total_skipped = sum(len(files) for files in self.skipped_files.values())
        print(f"\nTotal files processed: {total_processed}")
        print(f"Total files skipped: {total_skipped}")

        # Detailed Warnings and Errors Section
        if self.warnings or self.errors:
            print("\n=== Processing Issues ===")
            
            if self.warnings:
                print("\nConversion Warnings:")
                print("─" * 100)  # Longer separator line
                for i, warning in enumerate(self.warnings, 1):
                    # Split warning into parts for better formatting
                    if " (attachment in " in warning:
                        file_info, error_msg = warning.split(": ", 1)
                        file_part, location = file_info.split(" (attachment in ")
                        location = location.rstrip(")")
                        print(f"  {i}. File:     {file_part}")
                        print(f"     Location: {location}")
                        print(f"     Issue:    Failed to convert - will be skipped\n")
                    else:
                        print(f"  {i}. {warning}\n")
            
            if self.errors:
                print("\nCritical Errors:")
                print("─" * 100)  # Longer separator line
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}\n")
            
            # Summary of issues
            print("Issues Summary:")
            if self.warnings:
                print(f"  Conversion Warnings: {len(self.warnings)}")
            if self.errors:
                print(f"  Critical Errors: {len(self.errors)}")

        # Log detailed information at debug level only
        logger.debug("=== Detailed Processing Summary ===")
        for file_type, files in self.processed_files.items():
            for f in files:
                logger.debug(f"Processed {file_type}: {f}")
        for reason, files in self.skipped_files.items():
            for f in files:
                logger.debug(f"Skipped ({reason}): {f}")

class MarkdownProcessor:
    """Processes markdown and office documents."""

    def __init__(self, config: NovaConfig):
        """Initialize processor with configuration."""
        self.config = config
        self.output_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))
        self.summary = ProcessingSummary()
        
        # Initialize markdown parser
        self.md = MarkdownIt('commonmark', {'typographer': config.markdown.typographer})
        self.md.enable('table')
        self.md.enable('strikethrough')
        
        # Add plugins
        for plugin in config.markdown.plugins:
            if plugin == 'linkify':
                self.md.enable('linkify')
            elif plugin == 'image':
                self.md.enable('image')
        
        # Initialize document converter with image support
        self.converter = MarkItDown()
        
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

    def _setup_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
        print(f"\nProcessing directory: {input_dir}")
        print("Starting markdown parse phase...")
        
        # Get allowed extensions
        markdown_exts = {'.md', '.markdown'}
        office_exts = {'.docx', '.pptx', '.xlsx', '.pdf'}
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.heic', '.HEIC', '.webp'}
        text_exts = {'.html', '.csv', '.json', '.txt', '.xml'}  # Add text formats
        allowed_exts = markdown_exts | office_exts | image_exts | text_exts  # Include text formats
        
        # First, collect all markdown files and their attachment directories
        markdown_files = []
        attachment_dirs = set()
        for file_path in input_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in markdown_exts:
                markdown_files.append(file_path)
                # Add potential attachment directory
                attachment_dir = file_path.parent / file_path.stem
                if attachment_dir.is_dir():
                    attachment_dirs.add(attachment_dir)
        
        # Then collect standalone files (not in attachment directories)
        standalone_files = []
        for file_path in input_dir.rglob('*'):
            if file_path.is_file():
                # Skip files we've already processed or that are in attachment dirs
                if file_path.suffix.lower() in markdown_exts:
                    continue
                if any(str(file_path).startswith(str(d)) for d in attachment_dirs):
                    continue
                if file_path.suffix.lower() in office_exts:
                    standalone_files.append(file_path)
        
        # Process all files with progress bar
        total_files = len(markdown_files) + len(standalone_files)
        with tqdm(total=total_files, desc="Processing files") as progress:
            # Process markdown files first (they'll handle their own attachments)
            for file_path in markdown_files:
                self.process_markdown_with_attachments(file_path, progress)
            
            # Process standalone files
            for file_path in standalone_files:
                self.process_file(file_path, progress)
        
        # Display summary after processing
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
            
            # Convert to PIL Image
            image = heif_file.to_pillow()
            
            # Save as JPG
            image.save(tmp_path, 'JPEG', quality=95)
            
            return tmp_path
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise e

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

    def process_markdown_with_attachments(self, input_path: Path, progress: tqdm) -> None:
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
                
                # Process each file in the attachments directory
                for attachment in input_attachments_dir.iterdir():
                    if attachment.is_file():
                        suffix = attachment.suffix.lower()
                        
                        # Build the patterns to match both full markdown links and bare references
                        filename = attachment.name
                        filename_encoded = filename.replace('(', '%28').replace(')', '%29').replace(' ', '%20')
                        dir_encoded = input_path.stem.replace(' ', '%20')
                        old_ref_patterns = [
                            f'[{filename}]({dir_encoded}/{filename_encoded})<!-- {{"embed":"true"}} -->',  # Full markdown link with encoding and comment
                            f'[{filename}]({input_path.stem}/{filename_encoded})<!-- {{"embed":"true"}} -->',  # Full markdown link with partial encoding
                            f'[{filename}]({input_path.stem}/{filename})<!-- {{"embed":"true"}} -->',  # Full markdown link without encoding
                            f'[{filename}]({dir_encoded}/{filename_encoded})',  # Full markdown link with encoding
                            f'[{filename}]({input_path.stem}/{filename_encoded})',  # Full markdown link with partial encoding
                            f'[{filename}]({input_path.stem}/{filename})',  # Full markdown link without encoding
                            f'({input_path.stem}/{filename})',  # Bare reference
                        ]
                        
                        # Handle text-based formats
                        if suffix in {'.html', '.csv', '.json', '.txt', '.xml'}:
                            try:
                                output_md = output_attachments_dir / f"{attachment.stem}.md"
                                result = self._convert_text_file_to_markdown(attachment)
                                
                                # Write markdown output
                                with open(output_md, 'w', encoding='utf-8') as f:
                                    f.write(result)
                                
                                # Update markdown content to reference the new markdown file
                                new_ref = f'[{filename}]({output_path.stem}/{attachment.stem}.md)<!-- {{"embed":"true"}} -->'
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, new_ref)
                                
                                self.summary.add_processed('text', attachment)
                            except (FileConversionException, UnsupportedFormatException, Exception) as e:
                                warning = f"Could not process text file {attachment.name} (attachment in {rel_path}): {str(e)}"
                                print(f"\nWarning: {warning}")
                                self.summary.add_warning(warning)
                                self.summary.add_skipped('error', attachment)
                                
                                # Replace reference with error note
                                error_note = f"[⚠️ Failed to convert attachment: {filename} (Error: {str(e)})]<!-- {{'status':'error'}} -->"
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, error_note)
                        
                        # Handle images (including HEIC and WebP) using MarkItDown
                        elif suffix in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.HEIC'}:
                            try:
                                # Special handling for HEIC files
                                if suffix in {'.heic', '.HEIC'} and HEIF_SUPPORT:
                                    # Convert HEIC to JPG first
                                    jpg_path = self._convert_heic_to_jpg(attachment)
                                    try:
                                        # Convert JPG and extract metadata
                                        output_md = output_attachments_dir / f"{attachment.stem}.md"
                                        result = self.converter.convert(
                                            str(jpg_path),
                                            image_dir=str(output_attachments_dir)
                                        )
                                    finally:
                                        # Clean up temporary JPG
                                        if jpg_path.exists():
                                            jpg_path.unlink()
                                # Special handling for WebP files
                                elif suffix == '.webp':
                                    # Convert WebP to JPG first
                                    jpg_path = self._convert_webp_to_jpg(attachment)
                                    try:
                                        # Convert JPG and extract metadata
                                        output_md = output_attachments_dir / f"{attachment.stem}.md"
                                        result = self.converter.convert(
                                            str(jpg_path),
                                            image_dir=str(output_attachments_dir)
                                        )
                                    finally:
                                        # Clean up temporary JPG
                                        if jpg_path.exists():
                                            jpg_path.unlink()
                                else:
                                    # Handle other image formats directly
                                    output_md = output_attachments_dir / f"{attachment.stem}.md"
                                    result = self.converter.convert(
                                        str(attachment),
                                        image_dir=str(output_attachments_dir)
                                    )
                                
                                # Convert result to string if needed
                                if not isinstance(result, str):
                                    result = str(result)
                                
                                # Write markdown with metadata
                                with open(output_md, 'w', encoding='utf-8') as f:
                                    f.write(result)
                                
                                # Update markdown content to reference the new markdown file
                                new_ref = f'[{filename}]({output_path.stem}/{attachment.stem}.md)<!-- {{"embed":"true"}} -->'
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, new_ref)
                                
                                self.summary.add_processed('image', attachment)
                            except (FileConversionException, UnsupportedFormatException, Exception) as e:
                                warning = f"Could not process image {attachment.name} (attachment in {rel_path}): {str(e)}"
                                print(f"\nWarning: {warning}")
                                self.summary.add_warning(warning)
                                self.summary.add_skipped('error', attachment)
                                
                                # Replace reference with error note
                                error_note = f"[⚠️ Failed to convert image: {filename} (Error: {str(e)})]<!-- {{'status':'error'}} -->"
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, error_note)
                        
                        # Handle PDFs and Office documents
                        elif suffix in {'.pdf', '.docx', '.pptx', '.xlsx'}:
                            try:
                                output_md = output_attachments_dir / f"{attachment.stem}.md"
                                
                                # Special handling for PDFs
                                if suffix == '.pdf' and PYMUPDF_SUPPORT:
                                    result = self._convert_pdf_to_markdown(attachment)
                                else:
                                    result = self.converter.convert(
                                        str(attachment),
                                        image_dir=str(output_attachments_dir)
                                    )
                                
                                # Convert result to string if needed
                                if not isinstance(result, str):
                                    result = str(result)
                                
                                with open(output_md, 'w', encoding='utf-8') as f:
                                    f.write(result)
                                # Update markdown content to reference the new markdown file
                                new_ref = f'[{filename}]({output_path.stem}/{attachment.stem}.md)<!-- {{"embed":"true"}} -->'
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, new_ref)
                                self.summary.add_processed('pdf' if suffix == '.pdf' else 'office', attachment)
                            except (FileConversionException, UnsupportedFormatException, Exception) as e:
                                warning = f"Could not process {suffix[1:].upper()} file {attachment.name} (attachment in {rel_path}): {str(e)}"
                                print(f"\nWarning: {warning}")
                                self.summary.add_warning(warning)
                                self.summary.add_skipped('error', attachment)
                                
                                # Replace reference with error note
                                error_note = f"[⚠️ Failed to convert {suffix[1:].upper()} file: {filename} (Error: {str(e)})]<!-- {{'status':'error'}} -->"
                                for old_ref in old_ref_patterns:
                                    if old_ref in content:
                                        content = content.replace(old_ref, error_note)
            
            # Write the processed markdown with updated references
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.summary.add_processed('markdown', input_path)
            progress.set_description(f"Processing markdown: {input_path.name}")
            progress.update(1)
            
        except Exception as e:
            error = f"Failed to process markdown file {input_path.name}: {str(e)}"
            print(f"\nError: {error}")
            self.summary.add_error(error)
            self.summary.add_skipped('error', input_path)
            progress.update(1)
            # Don't raise the error, just continue with the next file

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