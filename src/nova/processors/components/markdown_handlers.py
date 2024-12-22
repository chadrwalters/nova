"""Markdown handling components for Nova processors."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from datetime import datetime

from . import MarkdownComponent
from ...core.config import NovaConfig, ProcessorConfig
from ...core.errors import ProcessingError
from ...core.logging import get_logger
from ..image_processor import ImageProcessor

class MarkitdownHandler(MarkdownComponent):
    """Handles markdown processing using markitdown."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig, image_processor: Optional[ImageProcessor] = None):
        """Initialize handler.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
            image_processor: Optional image processor instance
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        self.image_processor = image_processor
        
        # Add component-specific stats
        self.stats.update({
            'files_processed': 0,
            'images_processed': 0,
            'links_updated': 0
        })
    
    def process_markdown(self, content: str, source_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            source_path: Path to source file
            
        Returns:
            Processed markdown content
        """
        try:
            self.logger.info(f"Processing markdown file: {source_path}")
            
            # Process images in the content
            self.logger.info("Processing images in markdown content")
            
            # Regular expression to find image references
            # Handle both ![alt](path) and ![](path) formats, with optional whitespace
            image_pattern = r'^\*\s*(?:JPG|HEIC)(?::\s*|\s+)!\[(.*?)\]\(([^)]+)\)(?:\s*<!--\s*(\{.*?\})\s*-->)?$'
            
            # Process all images line by line
            lines = []
            for line in content.splitlines():
                # Debug logging
                if 'JPG' in line or 'HEIC' in line:
                    self.logger.info(f"Processing line: {line}")
                    match = re.match(image_pattern, line)
                    if match:
                        self.logger.info("Line matched pattern")
                        lines.append(self._process_image_match(match, source_path))
                    else:
                        self.logger.info("Line did not match pattern")
                        lines.append(line)
                else:
                    lines.append(line)
            
            # Update stats
            self.stats['files_processed'] += 1
            
            return '\n'.join(lines)
            
        except Exception as e:
            self.logger.error(f"Failed to process {source_path}: {e}")
            raise ProcessingError(f"Failed to process {source_path}: {e}") from e
    
    def convert_document(self, input_path: Path, output_path: Path) -> str:
        """Convert a document to markdown format.
        
        Args:
            input_path: Path to input document
            output_path: Path to output markdown file
            
        Returns:
            str: Converted markdown content
        """
        try:
            self.logger.info(f"Converting document: {input_path}")
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert based on file type
            suffix = input_path.suffix.lower()
            if suffix in ['.docx', '.doc']:
                return self._convert_docx(input_path, output_path)
            elif suffix in ['.pptx', '.ppt']:
                return self._convert_pptx(input_path, output_path)
            elif suffix in ['.xlsx', '.xls']:
                return self._convert_xlsx(input_path, output_path)
            elif suffix == '.pdf':
                return self._convert_pdf(input_path, output_path)
            elif suffix == '.csv':
                return self._convert_csv(input_path, output_path)
            else:
                raise ProcessingError(f"Unsupported document format: {suffix}")
            
        except Exception as e:
            self.logger.error(f"Failed to convert {input_path}: {e}")
            raise ProcessingError(f"Failed to convert {input_path}: {e}") from e
    
    def _convert_docx(self, input_path: Path, output_path: Path) -> str:
        """Convert DOCX to markdown."""
        from docx import Document
        
        doc = Document(str(input_path))
        content = []
        
        for para in doc.paragraphs:
            content.append(para.text)
        
        return '\n\n'.join(content)
    
    def _convert_pptx(self, input_path: Path, output_path: Path) -> str:
        """Convert PPTX to markdown."""
        from pptx import Presentation
        
        prs = Presentation(str(input_path))
        content = []
        
        for slide in prs.slides:
            slide_content = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slide_content.append(shape.text)
            content.append('\n'.join(slide_content))
        
        return '\n\n'.join(content)
    
    def _convert_xlsx(self, input_path: Path, output_path: Path) -> str:
        """Convert XLSX to markdown."""
        from openpyxl import load_workbook
        from datetime import datetime
        
        def format_cell_value(value):
            """Format cell value for markdown."""
            if value is None:
                return ''
            elif isinstance(value, datetime):
                return value.strftime('%Y-%m-%d')  # Format dates as YYYY-MM-DD
            else:
                return str(value).strip()
        
        wb = load_workbook(str(input_path))
        content = []
        
        for sheet in wb:
            # Add sheet name as header
            content.append(f"# {sheet.title}\n")
            
            # Process each sheet
            row_idx = 1
            while row_idx <= sheet.max_row:
                # Find the start of a table (non-empty row)
                if any(cell.value for cell in sheet[row_idx]):
                    table_content = []
                    header_cells = list(sheet[row_idx])
                    
                    # Look ahead for merged header rows
                    next_row_idx = row_idx + 1
                    while next_row_idx <= sheet.max_row:
                        next_row = list(sheet[next_row_idx])
                        if not any(cell.value for cell in next_row):
                            break
                        if all(isinstance(cell.value, (str, type(None))) for cell in next_row):
                            header_cells.extend(next_row)
                            next_row_idx += 1
                        else:
                            break
                    
                    # Build header from merged rows
                    headers = []
                    for cell in header_cells:
                        value = format_cell_value(cell.value)
                        if value:
                            headers.append(value)
                    
                    # Skip if no valid headers
                    if not headers:
                        row_idx = next_row_idx
                        continue
                    
                    # Add header row
                    table_content.append(' | '.join(headers))
                    
                    # Add separator row
                    table_content.append('|'.join(['---' for _ in headers]))
                    
                    # Process data rows
                    data_start_row = next_row_idx
                    while data_start_row <= sheet.max_row:
                        row = list(sheet[data_start_row])
                        row_content = []
                        is_empty_row = True
                        
                        # Process each cell in the row
                        for cell in row[:len(headers)]:  # Only process cells up to header count
                            value = format_cell_value(cell.value)
                            row_content.append(value)
                            if value:
                                is_empty_row = False
                        
                        # Skip empty rows
                        if is_empty_row:
                            data_start_row += 1
                            continue
                        
                        # Pad row if needed
                        while len(row_content) < len(headers):
                            row_content.append('')
                        
                        # Add data row
                        table_content.append(' | '.join(row_content))
                        data_start_row += 1
                    
                    # Add table to content with spacing
                    content.extend(['', *table_content, ''])
                    row_idx = data_start_row
                else:
                    row_idx += 1
            
            # Add blank line between sheets
            content.append('')
        
        return '\n'.join(content)
    
    def _convert_pdf(self, input_path: Path, output_path: Path) -> str:
        """Convert PDF to markdown."""
        import warnings
        from pypdf import PdfReader
        
        # Suppress PyPDF deprecation warning about ARC4
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='ARC4 has been moved to cryptography.hazmat.decrepit.*',
                category=DeprecationWarning
            )
            reader = PdfReader(str(input_path))
            content = []
            
            for page in reader.pages:
                content.append(page.extract_text())
            
            return '\n\n'.join(content)
    
    def _convert_csv(self, input_path: Path, output_path: Path) -> str:
        """Convert CSV to markdown."""
        import csv
        import chardet
        
        # Detect encoding
        with open(input_path, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result['encoding']
        
        # Read CSV with detected encoding
        content = []
        with open(input_path, 'r', encoding=encoding) as f:
            reader = csv.reader(f)
            for row in reader:
                content.append(' | '.join(row))
        
        return '\n'.join(content)
    
    def _process_image_match(self, match: re.Match, source_path: Path) -> str:
        """Process a single image match and return updated markdown."""
        try:
            alt_text, image_path, metadata_json = match.groups()
            self.logger.info(f"Processing image: {image_path}")
            
            # URL decode the image path
            image_path = image_path.replace('%20', ' ')
            
            # Resolve image path relative to markdown file
            full_image_path = source_path.parent / image_path
            if not full_image_path.exists():
                error = f"Image not found: {full_image_path}"
                self.logger.warning(error)
                return match.group(0)
            
            # Process image
            output_dir = source_path.parent / Path(image_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get the processed image path relative to the markdown file
            processed_path = output_dir / full_image_path.name
            rel_path = processed_path.relative_to(source_path.parent)
            
            # URL encode spaces in the path
            rel_path_str = str(rel_path).replace(' ', '%20')
            
            # Use original alt text if not empty, otherwise use filename
            alt = alt_text if alt_text else Path(image_path).stem
            prefix = match.group(0).split('!')[0]  # Get the "* JPG:" or "* HEIC:" part
            
            # Update stats
            self.stats['images_processed'] += 1
            
            return f"{prefix}![{alt}]({rel_path_str})"
            
        except Exception as e:
            error = f"Failed to process image match: {str(e)}"
            self.logger.warning(error)
            return match.group(0)

class ConsolidationHandler(MarkdownComponent):
    """Handles markdown consolidation."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize handler.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
        # Add component-specific stats
        self.stats.update({
            'files_consolidated': 0,
            'total_files': 0,
            'total_size': 0
        })
    
    def process_markdown(self, content: str, source_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            source_path: Path to source file
            
        Returns:
            Processed markdown content
        """
        # This handler doesn't modify individual markdown files
        return content
    
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
                    
                    # Update stats
                    self.stats['files_consolidated'] += 1
                    self.stats['total_size'] += len(content)
            
            # Write consolidated content
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(consolidated_content))
            
            # Update total files stat
            self.stats['total_files'] = len(input_files)
            
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to consolidate markdown: {e}") from e