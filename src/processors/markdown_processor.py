"""Markdown processor for converting documents to markdown format."""

import os
import shutil
from pathlib import Path
from typing import Set, Dict, List
from dataclasses import dataclass, field
from io import StringIO

from markdown_it import MarkdownIt
from markitdown import MarkItDown
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from tqdm import tqdm

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
        'office': []
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

        # Warnings
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        # Errors
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        # Total summary
        total_processed = sum(len(files) for files in self.processed_files.values())
        total_skipped = sum(len(files) for files in self.skipped_files.values())
        print(f"\nTotal files processed: {total_processed}")
        print(f"Total files skipped: {total_skipped}")

        # Log detailed information
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
        
        # Initialize office document converter
        self.office_converter = MarkItDown()

    def _setup_directories(self):
        """Create required directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
            elif suffix == '.pdf':
                try:
                    self._process_pdf_file(input_path, output_path.with_suffix('.md'))
                    self.summary.add_processed('pdf', input_path)
                    progress.set_description(f"Processing PDF: {input_path.name}")
                except Exception as e:
                    # Find parent markdown file if this is an attachment
                    parent_file = None
                    parent_path = None
                    
                    # Look for a markdown file with the same name as the parent directory
                    parent_dir = input_path.parent
                    possible_parent = parent_dir.with_suffix('.md')
                    if possible_parent.exists():
                        parent_file = possible_parent.name
                        parent_path = possible_parent.relative_to(os.getenv('NOVA_INPUT_DIR'))
                    else:
                        possible_parent = parent_dir.with_suffix('.markdown')
                        if possible_parent.exists():
                            parent_file = possible_parent.name
                            parent_path = possible_parent.relative_to(os.getenv('NOVA_INPUT_DIR'))
                    
                    warning = f"Could not convert PDF {input_path.name}"
                    if parent_file:
                        warning += f" (attachment in {parent_path})"
                    warning += f": {str(e)}"
                    
                    logger.warning(warning)
                    self.summary.add_warning(warning)
                    self.summary.add_skipped('error', input_path)
                    progress.set_description(f"Skipped PDF: {input_path.name}")
            elif suffix in ['.doc', '.ppt', '.xls']:
                warning = f"Skipping legacy format file {input_path.name}"
                logger.warning(warning)
                self.summary.add_warning(warning)
                self.summary.add_skipped('legacy_format', input_path)
                progress.set_description(f"Skipping legacy format: {input_path.name}")
            elif suffix in ['.docx', '.pptx', '.xlsx']:
                self._process_office_file(input_path, output_path.with_suffix('.md'))
                self.summary.add_processed('office', input_path)
                progress.set_description(f"Processing office file: {input_path.name}")
            else:
                warning = f"Skipping unsupported format: {input_path.name}"
                logger.warning(warning)
                self.summary.add_warning(warning)
                self.summary.add_skipped('unsupported_format', input_path)
                progress.set_description(f"Skipping unsupported: {input_path.name}")
            
            progress.update(1)
            logger.debug(f"Processed file saved to: {output_path}")
            
        except Exception as e:
            error = f"Failed to process {input_path.name}: {str(e)}"
            print(f"\nError: {error}")  # Print errors to console
            logger.error(error)
            self.summary.add_error(error)
            self.summary.add_skipped('error', input_path)
            progress.update(1)
            raise ProcessingError(error)

    def process_directory(self, input_dir: Path) -> None:
        """Process all files in a directory."""
        print(f"\nProcessing directory: {input_dir}")
        logger.info(f"Processing directory: {input_dir}")
        
        # Get allowed extensions (only supported formats)
        markdown_exts = {'.md', '.markdown'}
        office_exts = {'.docx', '.pptx', '.xlsx', '.pdf'}  # Only modern Office formats
        allowed_exts = markdown_exts | office_exts
        
        # Get list of files to process
        files_to_process = []
        for file_path in input_dir.rglob('*'):
            # Skip files in attachment directories (they'll be copied with their parent)
            if any(parent.name.endswith(('.md', '.markdown')) for parent in file_path.parents):
                continue
            
            if file_path.is_file():
                if file_path.suffix.lower() in allowed_exts:
                    files_to_process.append(file_path)
                elif file_path.suffix.lower() in {'.doc', '.ppt', '.xls'}:
                    warning = f"Skipping legacy format: {file_path.name}"
                    logger.warning(warning)
                    self.summary.add_warning(warning)
                    self.summary.add_skipped('legacy_format', file_path)
        
        # Process files with progress bar
        with tqdm(total=len(files_to_process), desc="Processing files") as progress:
            for file_path in files_to_process:
                self.process_file(file_path, progress)
        
        # Display summary after processing
        self.summary.display()

    def _process_markdown_file(self, input_path: Path, output_path: Path) -> None:
        """Process a markdown file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse and validate markdown
        self.md.parse(content)
        
        # Write processed markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _process_pdf_file(self, input_path: Path, output_path: Path) -> None:
        """Convert PDF to markdown using pdfminer.six."""
        from pdfminer.high_level import extract_text
        
        try:
            # Extract text directly using high-level API
            text = extract_text(
                str(input_path),
                laparams=LAParams(
                    line_margin=0.2,
                    word_margin=0.1,
                    char_margin=1.0,
                    boxes_flow=0.5,
                    detect_vertical=True,
                    all_texts=True
                )
            )
            
            # Skip if no text was extracted
            if not text or not text.strip():
                raise ProcessingError("No text could be extracted from PDF")
            
            # Basic markdown formatting with improved whitespace handling
            lines = []
            current_paragraph = []
            
            for line in text.split('\n'):
                line = line.strip()
                if line:
                    current_paragraph.append(line)
                elif current_paragraph:
                    lines.append(' '.join(current_paragraph))
                    lines.append('')  # Add blank line between paragraphs
                    current_paragraph = []
            
            # Handle any remaining paragraph
            if current_paragraph:
                lines.append(' '.join(current_paragraph))
            
            markdown_content = '\n'.join(lines).strip()
            
            # Only write if we have content
            if markdown_content:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
            else:
                raise ProcessingError("No content after formatting")
                
        except Exception as e:
            logger.warning(f"PDF extraction failed for {input_path.name}: {str(e)}")
            # Copy the original PDF as fallback
            shutil.copy2(input_path, output_path.with_suffix('.pdf'))
            raise ProcessingError(f"PDF extraction failed: {str(e)}")

    def _process_office_file(self, input_path: Path, output_path: Path) -> None:
        """Convert office document to markdown."""
        # Set up image directory in the same directory as the output file
        image_dir = output_path.parent / output_path.stem
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert document with image handling
        result = self.office_converter.convert(
            str(input_path),
            image_dir=str(image_dir)  # Tell markitdown where to save images
        )
        
        # Get markdown content
        if isinstance(result, str):
            markdown_content = result
        else:
            try:
                # Try to get markdown from result object
                markdown_content = str(result)
            except Exception as e:
                logger.warning(f"Failed to convert result to string, trying fallback methods for {input_path}")
                try:
                    # Try direct conversion as fallback
                    markdown_content = self.office_converter.convert_local(str(input_path))
                except Exception as e:
                    logger.error(f"All conversion methods failed for {input_path}: {str(e)}")
                    raise ProcessingError(f"Failed to convert {input_path}: {str(e)}")
        
        # Write converted markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)