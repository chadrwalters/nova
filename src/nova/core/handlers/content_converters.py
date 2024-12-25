"""Content converters for different file formats."""

import csv
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Type, Optional

import aiofiles
import docx
import openpyxl
import PyPDF2
from pptx import Presentation
import yaml

class BaseContentConverter(ABC):
    """Base class for content converters."""
    
    @abstractmethod
    async def convert(self, file_path: Path) -> str:
        """Convert file content to markdown.
        
        Args:
            file_path: Path to file to convert
            
        Returns:
            Markdown representation of file content
            
        Raises:
            Exception: If conversion fails
        """
        pass

class MarkdownConverter(BaseContentConverter):
    """Converter for markdown files."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert markdown file.
        
        Just reads the file as is since it's already markdown.
        Validates the content and extracts any metadata.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Markdown content
        """
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Check for YAML frontmatter
        if content.startswith('---'):
            try:
                # Find end of frontmatter
                end = content.find('---', 3)
                if end != -1:
                    # Parse frontmatter
                    frontmatter = yaml.safe_load(content[3:end])
                    # Reconstruct content with validated frontmatter
                    content = f"---\n{yaml.dump(frontmatter)}---\n{content[end+4:]}"
            except yaml.YAMLError:
                pass  # Invalid frontmatter, return as is
                
        return content

class DocxConverter(BaseContentConverter):
    """Converter for Word documents."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert Word document to markdown.
        
        Args:
            file_path: Path to Word document
            
        Returns:
            Markdown representation of document
        """
        doc = docx.Document(file_path)
        
        # Convert paragraphs to markdown
        markdown = []
        for para in doc.paragraphs:
            # Skip empty paragraphs
            if not para.text.strip():
                continue
                
            # Convert paragraph style to markdown
            if para.style.name.startswith('Heading'):
                level = para.style.name[-1]
                markdown.append(f"{'#' * int(level)} {para.text}")
            else:
                markdown.append(para.text)
            
            # Add newline after paragraph
            markdown.append('')
        
        return '\n'.join(markdown)

class PptxConverter(BaseContentConverter):
    """Converter for PowerPoint presentations."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert PowerPoint presentation to markdown.
        
        Args:
            file_path: Path to PowerPoint file
            
        Returns:
            Markdown representation of presentation
        """
        prs = Presentation(file_path)
        
        # Convert slides to markdown
        markdown = []
        for i, slide in enumerate(prs.slides, 1):
            # Add slide header
            markdown.append(f"# Slide {i}")
            markdown.append('')
            
            # Convert shapes to text
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    markdown.append(shape.text)
                    markdown.append('')
            
            # Add slide separator
            markdown.append('---')
            markdown.append('')
        
        return '\n'.join(markdown)

class XlsxConverter(BaseContentConverter):
    """Converter for Excel spreadsheets."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert Excel spreadsheet to markdown.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Markdown representation of spreadsheet
        """
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        
        # Convert worksheet to markdown table
        markdown = []
        
        # Get dimensions
        max_row = sheet.max_row
        max_col = sheet.max_column
        
        # Create header row
        header = []
        for col in range(1, max_col + 1):
            cell = sheet.cell(row=1, column=col)
            header.append(str(cell.value or ''))
        markdown.append('| ' + ' | '.join(header) + ' |')
        
        # Add separator row
        markdown.append('|' + '|'.join(['---'] * max_col) + '|')
        
        # Add data rows
        for row in range(2, max_row + 1):
            data = []
            for col in range(1, max_col + 1):
                cell = sheet.cell(row=row, column=col)
                data.append(str(cell.value or ''))
            markdown.append('| ' + ' | '.join(data) + ' |')
        
        return '\n'.join(markdown)

class PdfConverter(BaseContentConverter):
    """Converter for PDF documents."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert PDF document to markdown.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Markdown representation of document
        """
        reader = PyPDF2.PdfReader(file_path)
        
        # Convert pages to markdown
        markdown = []
        for i, page in enumerate(reader.pages, 1):
            # Add page header
            markdown.append(f"# Page {i}")
            markdown.append('')
            
            # Extract and clean text
            text = page.extract_text()
            if text:
                markdown.append(text)
                markdown.append('')
            
            # Add page separator
            markdown.append('---')
            markdown.append('')
        
        return '\n'.join(markdown)

class CsvConverter(BaseContentConverter):
    """Converter for CSV files."""
    
    async def convert(self, file_path: Path) -> str:
        """Convert CSV file to markdown.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Markdown representation of CSV data
        """
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # Parse CSV content
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        
        if not rows:
            return ''
        
        # Convert to markdown table
        markdown = []
        
        # Add header row
        markdown.append('| ' + ' | '.join(rows[0]) + ' |')
        
        # Add separator row
        markdown.append('|' + '|'.join(['---'] * len(rows[0])) + '|')
        
        # Add data rows
        for row in rows[1:]:
            markdown.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(markdown)

class ContentConverterFactory:
    """Factory for creating content converters."""
    
    _converters: Dict[str, Type[BaseContentConverter]] = {
        'md': MarkdownConverter,
        'docx': DocxConverter,
        'doc': DocxConverter,
        'pptx': PptxConverter,
        'ppt': PptxConverter,
        'xlsx': XlsxConverter,
        'xls': XlsxConverter,
        'pdf': PdfConverter,
        'csv': CsvConverter
    }
    
    @classmethod
    def get_converter(cls, file_type: str) -> Optional[BaseContentConverter]:
        """Get converter for file type.
        
        Args:
            file_type: File extension without dot
            
        Returns:
            Converter instance if supported, None otherwise
        """
        converter_class = cls._converters.get(file_type.lower())
        if converter_class:
            return converter_class()
        return None