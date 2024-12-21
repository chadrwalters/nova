"""Markdown processor module for Nova document processor."""

from pathlib import Path
from typing import Dict, List, Optional
import shutil
import re
import subprocess
from dataclasses import dataclass, field
import csv

from pydantic import BaseModel

from .base import BaseProcessor
from .components.markdown_handlers import MarkitdownHandler
from ..core.config import ProcessorConfig, NovaConfig
from ..core.logging import get_logger

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
        'unchanged': [],
        'unsupported': [],
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

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files."""
    
    def _setup(self) -> None:
        """Setup markdown processor requirements."""
        # Initialize handler with config
        self.markdown_handler = MarkitdownHandler(self.nova_config)
        self.logger = get_logger(__name__)
        self.summary = ProcessingSummary()
    
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
                self.logger.info(f"Processing attachments directory: {attachments_dir}")
                
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
                                output_file = self._process_pdf(file_path, output_file)
                                self.summary.add_processed('pdf', file_path)
                            elif suffix in ['.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.csv']:
                                output_file = self._process_office_doc(file_path, output_file)
                                self.summary.add_processed('office', file_path)
                            elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic']:
                                output_file = self._process_image(file_path, output_file)
                                self.summary.add_processed('image', file_path)
                            else:
                                # Just copy other files
                                shutil.copy2(file_path, output_file)
                                self.summary.add_processed('other', file_path)
                            
                            # Track link update if file was converted to markdown
                            if output_file.suffix == '.md':
                                # Get the original and new paths in URL-encoded format
                                old_path = str(output_attachments_dir.name) + '/' + str(rel_path)
                                old_path = old_path.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
                                
                                new_path = str(output_attachments_dir.name) + '/' + str(output_file.relative_to(output_attachments_dir))
                                new_path = new_path.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
                                
                                link_updates[old_path] = new_path
                                
                        except Exception as e:
                            error = f"Failed to process attachment {file_path.name}: {str(e)}"
                            self.logger.error(error)
                            self.summary.add_error(error)
                            self.summary.add_skipped('error', file_path)
                
                # Update links in markdown content using regex to preserve link text
                for old_path, new_path in link_updates.items():
                    # Create regex pattern to match the full link with metadata
                    pattern = re.compile(
                        r'\[(.*?)\]\(' + re.escape(old_path) + r'\)<!-- \{"embed":"true"\} -->'
                    )
                    
                    # Replace the link in the content, preserving the original link text
                    processed_content = pattern.sub(
                        rf'[\1]({new_path})<!-- {{"embed":"true"}} -->',
                        processed_content
                    )
            
            # Write processed markdown
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            self.summary.add_processed('markdown', input_path)
            return output_path
            
        except Exception as e:
            error = f"Failed to process {input_path.name}: {str(e)}"
            self.logger.error(error)
            self.summary.add_error(error)
            self.summary.add_skipped('error', file_path)
            raise
    
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
                
                self.logger.info(f"Successfully converted CSV file: {input_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to convert CSV file {input_path}: {e}")
                raise
        else:
            # Convert other office docs using markitdown
            content = self.markdown_handler.convert_document(input_path)
            
            # Write markdown output
            with open(md_output, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return md_output
        
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding by trying different encodings.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            Detected encoding
        """
        encodings = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                return encoding
            except UnicodeDecodeError:
                continue
        
        raise UnicodeDecodeError(f"Could not decode {file_path} with any supported encoding")
    
    def _process_image(self, input_path: Path, output_path: Path) -> Path:
        """Process an image file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        if input_path.suffix.lower() == '.heic':
            # Convert HEIC to JPG using sips
            jpg_output = output_path.with_suffix('.jpg')
            subprocess.run(['sips', '-s', 'format', 'jpeg', str(input_path), '--out', str(jpg_output)], check=True)
            return jpg_output
        else:
            # Copy other images as is
            shutil.copy2(input_path, output_path)
            return output_path