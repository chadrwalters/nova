"""Markdown handler components."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import csv
import json
import logging

from markitdown import MarkItDown
from rich.console import Console

from . import ProcessorComponent
from ...core.config import NovaConfig
from ...core.errors import MarkdownProcessingError
from ...core.logging import get_logger

logger = get_logger(__name__)
console = Console()

class MarkitdownHandler(ProcessorComponent):
    """Handles markdown processing using Microsoft's markitdown."""
    
    def __init__(self, config: NovaConfig, image_processor=None, output_dir=None):
        """Initialize handler.
        
        Args:
            config: Nova configuration
            image_processor: Optional image processor instance
            output_dir: Optional output directory path
        """
        super().__init__(config)
        
        # Initialize markdown converter
        self.converter = MarkItDown()
        
        # Store image processor and output directory
        self.image_processor = image_processor
        self.output_dir = output_dir
        
        # Initialize logger
        self.logger = logger
        logger.debug(f"Initialized MarkitdownHandler with image_processor={image_processor}, output_dir={output_dir}")
    
    def process_markdown(self, content: str, source_path: Path) -> tuple[str, dict]:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            source_path: Path to source file
            
        Returns:
            Tuple of (processed content, stats)
        """
        try:
            self.logger.info(f"Processing markdown file: {source_path}")
            
            # Initialize stats for this file
            file_stats = {
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
            
            # Check if we have image processor
            if not self.image_processor:
                self.logger.warning("No image processor available - skipping image processing")
                return content, file_stats
            
            # Process images in the content
            self.logger.info("Processing images in markdown content")
            
            # Regular expression to find image references
            # Handle both ![alt](path) and ![](path) formats, with optional whitespace
            image_pattern = r'^\*\s*(?:JPG|HEIC)(?::\s*|\s+)!\[(.*?)\]\(([^)]+)\)(?:\s*<!--\s*(\{.*?\})\s*-->)?$'
            
            def process_image_match(match) -> str:
                """Process a single image match and return updated markdown."""
                file_stats['images']['total'] += 1
                
                alt_text, image_path, metadata_json = match.groups()
                self.logger.info(f"Processing image: {image_path}")
                
                # URL decode the image path
                image_path = image_path.replace('%20', ' ')
                
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                # Resolve image path relative to markdown file
                full_image_path = source_path.parent / image_path
                if not full_image_path.exists():
                    error = f"Image not found: {full_image_path}"
                    self.logger.warning(error)
                    file_stats['images']['failed'] += 1
                    return match.group(0)
                
                try:
                    # Track original size
                    original_size = full_image_path.stat().st_size
                    file_stats['images']['total_original_size'] += original_size
                    
                    # Track format
                    img_format = full_image_path.suffix.lower()
                    file_stats['images']['formats'][img_format] = file_stats['images']['formats'].get(img_format, 0) + 1
                    
                    # Process image - store in same directory structure as original
                    output_dir = source_path.parent / Path(image_path).parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    metadata = self.image_processor.process_image(
                        input_path=full_image_path,
                        output_dir=output_dir
                    )
                    
                    if metadata:
                        file_stats['images']['processed'] += 1
                        file_stats['images']['total_processed_size'] += metadata.size
                        
                        # Get the processed image path relative to the markdown file
                        processed_path = Path(metadata.processed_path)
                        rel_path = processed_path.relative_to(source_path.parent)
                        
                        # URL encode spaces in the path
                        rel_path_str = str(rel_path).replace(' ', '%20')
                        
                        if metadata.description:
                            file_stats['images']['with_description'] += 1
                            # Generate markdown with description and keep the format prefix
                            prefix = match.group(0).split('!')[0]  # Get the "* JPG:" or "* HEIC:" part
                            return f"{prefix}![{metadata.description}]({rel_path_str})"
                        else:
                            # Use original alt text if not empty, otherwise use filename
                            alt = alt_text if alt_text else Path(image_path).stem
                            prefix = match.group(0).split('!')[0]  # Get the "* JPG:" or "* HEIC:" part
                            return f"{prefix}![{alt}]({rel_path_str})"
                    else:
                        file_stats['images']['failed'] += 1
                        return match.group(0)
                    
                except Exception as e:
                    error = f"Failed to process {full_image_path}: {str(e)}"
                    self.logger.warning(error)
                    file_stats['images']['failed'] += 1
                    return match.group(0)
            
            # Process all images line by line
            lines = []
            for line in content.splitlines():
                # Debug logging
                if 'JPG' in line or 'HEIC' in line:
                    self.logger.info(f"Processing line: {line}")
                    match = re.match(image_pattern, line)
                    if match:
                        self.logger.info("Line matched pattern")
                        lines.append(process_image_match(match))
                    else:
                        self.logger.info("Line did not match pattern")
                        lines.append(line)
                else:
                    lines.append(line)
            
            # Log summary
            if file_stats['images']['total'] > 0:
                self.logger.info(f"Processed {file_stats['images']['processed']}/{file_stats['images']['total']} images")
                self.logger.info(f"Generated descriptions for {file_stats['images']['with_description']} images")
                if file_stats['images']['failed'] > 0:
                    self.logger.warning(f"Failed to process {file_stats['images']['failed']} images")
            
            return '\n'.join(lines), file_stats
            
        except Exception as e:
            self.logger.error(f"Failed to process {source_path}: {e}")
            raise MarkdownProcessingError(f"Failed to process {source_path}: {e}") from e
    
    def convert_document(self, input_path: Path) -> str:
        """Convert a document to markdown.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Markdown content
        """
        try:
            # Handle CSV files differently
            if input_path.suffix.lower() == '.csv':
                print(f"Converting CSV file: {input_path}")  # Debug log
                result = self._convert_csv_to_markdown(input_path)
                print(f"CSV conversion result length: {len(result)}")  # Debug log
                return result
            
            # Convert other documents using markitdown
            # Use absolute path to handle spaces and special characters
            abs_path = input_path.resolve()
            print(f"Converting non-CSV file: {abs_path}")  # Debug log
            
            # Try convert_local first
            result = self.converter.convert_local(str(abs_path))
            
            if result is None:
                raise MarkdownProcessingError(f"Failed to convert {input_path}: markitdown returned None")
            
            # Extract text content from result
            if not result.text_content:
                # Try to convert using convert() method instead
                result = self.converter.convert(str(abs_path))
                if not result.text_content:
                    raise MarkdownProcessingError(f"Failed to convert {input_path}: no text content in result")
            
            # Add title if available
            content = []
            if hasattr(result, 'title') and result.title:
                content.append(f"# {result.title}\n")
            
            # Add text content
            content.append(result.text_content)
            
            return '\n'.join(content)
            
        except Exception as e:
            print(f"Error converting document: {str(e)}")  # Debug log
            raise MarkdownProcessingError(f"Failed to convert {input_path}: {e}") from e
            
    def _convert_csv_to_markdown(self, input_path: Path) -> str:
        """Convert CSV file to markdown table.
        
        Args:
            input_path: Path to CSV file
            
        Returns:
            Markdown content
        """
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
                # Escape any pipe characters in cells
                escaped_row = [cell.replace('|', '\\|') for cell in row]
                md_table.append("| " + " | ".join(escaped_row) + " |")
            
            return f"# {input_path.stem}\n\n" + "\n".join(md_table) + f"\n\n*File encoding: {encoding}*"
            
        except Exception as e:
            raise MarkdownProcessingError(f"Failed to convert CSV file {input_path}: {e}")
            
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
    
    def _handle_images(self, content: str, source_path: Path) -> tuple[str, dict]:
        """Handle images in markdown content."""
        try:
            self.logger.debug("Starting _handle_images")
            
            # Track image processing stats
            stats = {
                'total': 0,
                'processed': 0,
                'with_description': 0,
                'failed': 0,
                'total_original_size': 0,
                'total_processed_size': 0,
                'heic_converted': 0,
                'formats': {},
                'errors': []
            }
            
            # Regular expression to find image references
            image_pattern = r'(.*)!\[(.*?)\]\(([^)]+)\)(?:\s*<!--\s*(\{.*?\})\s*-->)?'
            
            # Find all matches first to see what we're dealing with
            matches = list(re.finditer(image_pattern, content))
            if matches:
                console.print(f"\n[title]Found {len(matches)} images in {source_path.name}[/]")
            
            def process_image_match(match) -> str:
                """Process a single image match and return updated markdown."""
                stats['total'] += 1
                
                prefix, alt_text, image_path, metadata_json = match.groups()
                console.print(f"[info]Processing image:[/] [path]{image_path}[/]")
                
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                # Resolve image path relative to markdown file
                full_image_path = source_path.parent / image_path
                if not full_image_path.exists():
                    error = f"Image not found: {full_image_path}"
                    console.print(f"[warning]{error}[/]")
                    stats['failed'] += 1
                    stats['errors'].append(error)
                    return match.group(0)
                
                try:
                    # Track original size
                    stats['total_original_size'] += full_image_path.stat().st_size
                    
                    # Track format
                    img_format = full_image_path.suffix.lower()
                    stats['formats'][img_format] = stats['formats'].get(img_format, 0) + 1
                    
                    # Process image
                    metadata = self.image_processor.process_image(
                        input_path=full_image_path,
                        output_dir=self.config.image.processed_dir,
                        metadata_dir=self.config.image.metadata_dir
                    )
                    
                    if metadata:
                        stats['processed'] += 1
                        stats['total_processed_size'] += metadata.size
                        
                        if metadata.description:
                            stats['with_description'] += 1
                        
                        # Generate markdown
                        description = metadata.description if metadata.description else alt_text
                        processed_path = Path(metadata.processed_path).relative_to(self.config.output_dir)
                        prefix_str = prefix if prefix else ""
                        prefix_str = prefix_str.rstrip() + " " if prefix_str else ""
                        return f"{prefix_str}![{description}]({processed_path})"
                    else:
                        stats['failed'] += 1
                        return match.group(0)
                    
                except Exception as e:
                    error = f"Failed to process {full_image_path}: {str(e)}"
                    console.print(f"[warning]{error}[/]")
                    stats['failed'] += 1
                    stats['errors'].append(error)
                    return match.group(0)
            
            # Process all images
            content = re.sub(image_pattern, process_image_match, content)
            
            return content, stats
            
        except Exception as e:
            self.logger.error(f"Error in _handle_images: {e}")
            raise MarkdownProcessingError(f"Failed to handle images: {e}") from e

class ConsolidationHandler(ProcessorComponent):
    """Handles markdown consolidation."""
    
    def __init__(self, config: NovaConfig):
        """Initialize handler.
        
        Args:
            config: Nova configuration
        """
        super().__init__(config)
        self.parser = MarkItDown()
    
    def consolidate_markdown(self, input_files: List[Path], output_path: Path) -> Path:
        """Consolidate markdown files.
        
        Args:
            input_files: List of input files to consolidate
            output_path: Path to output file
            
        Returns:
            Path to consolidated file
        """
        try:
            # Sort files by date in filename (YYYYMMDD format)
            date_pattern = r'(\d{8})'
            sorted_files = sorted(
                input_files,
                key=lambda x: re.search(date_pattern, x.name).group(1) if re.search(date_pattern, x.name) else '00000000'
            )
            
            # Read and process each file
            consolidated_content = []
            for file_path in sorted_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Add file header
                    header = f"\n\n## {file_path.stem}\n\n"
                    consolidated_content.append(header)
                    
                    # Add processed content
                    consolidated_content.append(content)
            
            # Write consolidated content
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(consolidated_content))
            
            return output_path
            
        except Exception as e:
            raise MarkdownProcessingError(f"Failed to consolidate markdown: {e}") from e