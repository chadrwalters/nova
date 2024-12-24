"""Content conversion handlers for different file types."""

import os
import re
import json
import csv
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union, Set, Type
from bs4 import BeautifulSoup
import markdown
import pandas as pd
from docx import Document
import fitz  # PyMuPDF
from PIL import Image
import yaml
import docx
import openpyxl
import pptx
import datetime

from ...core.errors import ProcessingError
from ...core.utils.logging import get_logger

logger = get_logger(__name__)

class BaseContentConverter:
    """Base class for content converters."""
    
    def __init__(self):
        """Initialize the converter."""
        self.logger = get_logger(self.__class__.__name__)
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert file content to markdown.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        raise NotImplementedError("Subclasses must implement convert()")

class ContentConverterFactory:
    """Factory for creating content converters."""
    
    _converters: Dict[str, Type[BaseContentConverter]] = {}
    
    @classmethod
    def register(cls, name: str, converter_class: Type[BaseContentConverter]) -> None:
        """Register a converter class.
        
        Args:
            name: Name of the converter
            converter_class: Converter class to register
        """
        cls._converters[name] = converter_class
    
    @classmethod
    def create_converter(cls, name: str) -> BaseContentConverter:
        """Create a converter instance.
        
        Args:
            name: Name of the converter to create
            
        Returns:
            Converter instance
            
        Raises:
            ProcessingError: If converter not found
        """
        converter_class = cls._converters.get(name)
        if not converter_class:
            raise ProcessingError(f"No converter registered for: {name}")
        return converter_class()

class HTMLConverter(BaseContentConverter):
    """Converts HTML content to markdown."""
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert HTML to markdown.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else os.path.basename(file_path)
            
            # Extract metadata
            metadata = {
                'title': title,
                'original_format': 'html',
                'tables': len(soup.find_all('table')),
                'images': len(soup.find_all('img')),
                'links': len(soup.find_all('a'))
            }
            
            # Clean up HTML
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
            
            # Convert tables to markdown format
            for table in soup.find_all('table'):
                markdown_table = ['|']
                
                # Get headers
                headers = table.find_all('th')
                if not headers:
                    headers = table.find_all('td', limit=1)[0].find_parent('tr').find_all('td')
                
                # Add header row
                for header in headers:
                    markdown_table[0] += f" {header.get_text().strip()} |"
                
                # Add separator row
                markdown_table.append('|' + '---|' * len(headers))
                
                # Add data rows
                rows = table.find_all('tr')[1:] if headers else table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    markdown_row = '|'
                    for cell in cells:
                        markdown_row += f" {cell.get_text().strip()} |"
                    markdown_table.append(markdown_row)
                
                # Replace table with markdown version
                table.replace_with(soup.new_string('\n'.join(markdown_table)))
            
            # Convert the cleaned HTML to markdown
            html_text = str(soup)
            markdown_content = markdown.markdown(html_text)
            
            # Clean up markdown
            # Remove extra newlines
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            # Add title as heading if not present
            if not markdown_content.startswith('# '):
                markdown_content = f"# {title}\n\n{markdown_content}"
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert HTML file {file_path}: {str(e)}")
            raise ProcessingError(f"HTML conversion failed: {str(e)}") from e

class CSVConverter(BaseContentConverter):
    """Converts CSV content to markdown tables."""
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert CSV to markdown table.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ProcessingError(f"Could not read CSV file with any supported encoding")
            
            # Extract metadata
            metadata = {
                'original_format': 'csv',
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist()
            }
            
            # Convert to markdown table
            markdown_lines = []
            
            # Add header
            header = '| ' + ' | '.join(str(col) for col in df.columns) + ' |'
            markdown_lines.append(header)
            
            # Add separator
            separator = '|' + '---|' * len(df.columns)
            markdown_lines.append(separator)
            
            # Add data rows
            for _, row in df.iterrows():
                markdown_row = '| ' + ' | '.join(str(cell) for cell in row) + ' |'
                markdown_lines.append(markdown_row)
            
            markdown_content = '\n'.join(markdown_lines)
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert CSV file {file_path}: {str(e)}")
            raise ProcessingError(f"CSV conversion failed: {str(e)}") from e

class JSONConverter(BaseContentConverter):
    """Converts JSON content to markdown code blocks."""
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert JSON to markdown code block.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Read JSON content
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
            
            # Extract metadata
            metadata = {
                'original_format': 'json',
                'size': os.path.getsize(file_path),
                'top_level_keys': list(json_content.keys()) if isinstance(json_content, dict) else None,
                'array_length': len(json_content) if isinstance(json_content, list) else None
            }
            
            # Convert to pretty-printed JSON
            formatted_json = json.dumps(json_content, indent=2)
            
            # Wrap in markdown code block
            markdown_content = f"```json\n{formatted_json}\n```"
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert JSON file {file_path}: {str(e)}")
            raise ProcessingError(f"JSON conversion failed: {str(e)}") from e

class TextConverter(BaseContentConverter):
    """Converts text files to markdown code blocks."""

    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert text to markdown code block.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Try to detect file type from extension
            ext = file_path.suffix.lower().lstrip('.')
            
            # Extract metadata
            metadata = {
                'original_format': ext,
                'size': os.path.getsize(file_path),
                'last_modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            }
            
            # For binary files, just add a note
            if ext in ['docx', 'doc', 'xlsx', 'xls', 'pdf']:
                markdown_content = f"```\n[Binary file: {file_path.name}]\n```"
                return markdown_content, metadata
            
            # For text files, try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # If all encodings fail, treat as binary
                markdown_content = f"```\n[Binary file: {file_path.name}]\n```"
            else:
                # Wrap text content in code block
                markdown_content = f"```{ext}\n{content}\n```"
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert text content: {str(e)}")
            raise ProcessingError(f"Text conversion failed: {str(e)}") from e

class OfficeConverter(BaseContentConverter):
    """Converts Office documents to markdown."""
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert Office document to markdown.
        
        Args:
            file_path: Path to Office document
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        # Determine file type from extension
        ext = file_path.suffix.lower()
        
        if ext in ['.docx', '.doc']:
            return self._convert_word(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self._convert_excel(file_path)
        elif ext in ['.pptx', '.ppt']:
            return self._convert_powerpoint(file_path)
        else:
            raise ProcessingError(f"Unsupported Office format: {ext}")
            
    def _convert_word(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert Word document to markdown.
        
        Args:
            file_path: Path to Word document
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Read document
            doc = docx.Document(file_path)
            
            # Extract metadata
            metadata = {
                'original_format': 'docx',
                'size': os.path.getsize(file_path),
                'paragraphs': len(doc.paragraphs),
                'tables': len(doc.tables),
                'sections': len(doc.sections)
            }
            
            # Convert content to markdown
            markdown_lines = []
            
            # Process paragraphs
            for paragraph in doc.paragraphs:
                if not paragraph.text.strip():
                    continue
                    
                # Handle heading styles
                style = paragraph.style.name.lower()
                if 'heading' in style:
                    level = int(style[-1]) if style[-1].isdigit() else 1
                    markdown_lines.append(f"{'#' * level} {paragraph.text}")
                else:
                    # Handle text formatting
                    text = paragraph.text
                    for run in paragraph.runs:
                        if run.bold:
                            text = text.replace(run.text, f"**{run.text}**")
                        if run.italic:
                            text = text.replace(run.text, f"*{run.text}*")
                    markdown_lines.append(text)
                
                markdown_lines.append('')  # Add blank line after paragraph
            
            # Process tables
            for table in doc.tables:
                # Table header
                header_row = []
                for cell in table.rows[0].cells:
                    header_row.append(cell.text.strip())
                markdown_lines.append('| ' + ' | '.join(header_row) + ' |')
                
                # Separator
                markdown_lines.append('|' + '---|' * len(header_row))
                
                # Table data
                for row in table.rows[1:]:
                    row_data = []
                    for cell in row.cells:
                        row_data.append(cell.text.strip())
                    markdown_lines.append('| ' + ' | '.join(row_data) + ' |')
                
                markdown_lines.append('')  # Add blank line after table
            
            markdown_content = '\n'.join(markdown_lines)
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert Word document {file_path}: {str(e)}")
            raise ProcessingError(f"Word conversion failed: {str(e)}") from e
            
    def _convert_excel(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert Excel document to markdown.
        
        Args:
            file_path: Path to Excel document
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Read workbook
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            
            # Extract metadata
            metadata = {
                'original_format': 'xlsx',
                'size': os.path.getsize(file_path),
                'sheets': len(workbook.sheetnames),
                'active_sheet': workbook.active.title
            }
            
            markdown_lines = []
            
            # Process each worksheet
            for sheet in workbook.worksheets:
                # Add sheet title
                markdown_lines.append(f"## Sheet: {sheet.title}")
                markdown_lines.append("")
                
                # Get dimensions
                min_row = sheet.min_row
                max_row = sheet.max_row
                min_col = sheet.min_column
                max_col = sheet.max_column
                
                if min_row == 0 or min_col == 0:
                    continue  # Skip empty sheets
                
                # Get column headers (first row)
                headers = []
                for col in range(min_col, max_col + 1):
                    cell = sheet.cell(min_row, col)
                    headers.append(str(cell.value or ''))
                
                # Add table header
                markdown_lines.append('| ' + ' | '.join(headers) + ' |')
                markdown_lines.append('|' + '---|' * len(headers))
                
                # Add data rows
                for row in range(min_row + 1, max_row + 1):
                    row_data = []
                    for col in range(min_col, max_col + 1):
                        cell = sheet.cell(row, col)
                        value = cell.value
                        # Format numbers and dates appropriately
                        if isinstance(value, (int, float)):
                            value = f"{value:,}"
                        elif isinstance(value, datetime.datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(value, datetime.date):
                            value = value.strftime('%Y-%m-%d')
                        row_data.append(str(value or ''))
                    markdown_lines.append('| ' + ' | '.join(row_data) + ' |')
                
                markdown_lines.append("")  # Add blank line after table
            
            markdown_content = '\n'.join(markdown_lines)
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert Excel document {file_path}: {str(e)}")
            raise ProcessingError(f"Excel conversion failed: {str(e)}") from e
            
    def _convert_powerpoint(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert PowerPoint presentation to markdown.
        
        Args:
            file_path: Path to PowerPoint document
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            # Read presentation
            presentation = pptx.Presentation(file_path)
            
            # Extract metadata
            metadata = {
                'original_format': 'pptx',
                'size': os.path.getsize(file_path),
                'slides': len(presentation.slides)
            }
            
            markdown_lines = []
            
            # Process each slide
            for slide_number, slide in enumerate(presentation.slides, 1):
                # Add slide header
                markdown_lines.append(f"## Slide {slide_number}")
                markdown_lines.append("")
                
                # Get slide title
                if slide.shapes.title:
                    markdown_lines.append(f"### {slide.shapes.title.text}")
                    markdown_lines.append("")
                
                # Process shapes (text boxes, tables, etc.)
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        # Process text
                        for paragraph in shape.text_frame.paragraphs:
                            if not paragraph.text.strip():
                                continue
                            
                            # Handle text formatting
                            text = paragraph.text
                            for run in paragraph.runs:
                                if run.font.bold:
                                    text = text.replace(run.text, f"**{run.text}**")
                                if run.font.italic:
                                    text = text.replace(run.text, f"*{run.text}*")
                            markdown_lines.append(text)
                            markdown_lines.append("")
                    
                    elif shape.has_table:
                        # Process table
                        table = shape.table
                        
                        # Table header
                        header_row = []
                        for cell in table.rows[0].cells:
                            header_row.append(cell.text.strip())
                        markdown_lines.append('| ' + ' | '.join(header_row) + ' |')
                        
                        # Separator
                        markdown_lines.append('|' + '---|' * len(header_row))
                        
                        # Table data
                        for row in table.rows[1:]:
                            row_data = []
                            for cell in row.cells:
                                row_data.append(cell.text.strip())
                            markdown_lines.append('| ' + ' | '.join(row_data) + ' |')
                        
                        markdown_lines.append("")
                
                # Add slide notes if present
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                    markdown_lines.append("#### Notes")
                    markdown_lines.append("")
                    markdown_lines.append(slide.notes_slide.notes_text_frame.text.strip())
                    markdown_lines.append("")
                
                markdown_lines.append("---")  # Add slide separator
                markdown_lines.append("")
            
            markdown_content = '\n'.join(markdown_lines)
            
            return markdown_content, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert PowerPoint document {file_path}: {str(e)}")
            raise ProcessingError(f"PowerPoint conversion failed: {str(e)}") from e

class PDFConverter(BaseContentConverter):
    """Converts PDF documents to markdown."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize PDF converter.
        
        Args:
            temp_dir: Optional directory for temporary files. If not provided, uses system temp dir.
        """
        super().__init__()
        self.temp_dir = temp_dir or Path('/tmp')
    
    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert PDF document to markdown.
        
        Args:
            file_path: Path to PDF document
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            import fitz  # PyMuPDF
            
            # Open PDF document
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = {
                'original_format': 'pdf',
                'size': os.path.getsize(file_path),
                'pages': len(doc),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'keywords': doc.metadata.get('keywords', '')
            }
            
            content = []
            
            # Process each page
            for page_num, page in enumerate(doc, 1):
                content.append(f"\n## Page {page_num}\n")
                
                # Extract text
                text = page.get_text()
                if text.strip():
                    content.append(text)
                
                # Extract images
                images = page.get_images()
                if images:
                    content.append("\n### Images\n")
                    for img_index, img in enumerate(images, 1):
                        xref = img[0]  # Cross-reference number
                        
                        # Get image data
                        base_image = doc.extract_image(xref)
                        if base_image:
                            # Get image info
                            image_data = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            # Generate unique filename
                            image_filename = f"page{page_num}_image{img_index}.{image_ext}"
                            
                            # Save image to temp file
                            temp_path = self.temp_dir / image_filename
                            with open(temp_path, 'wb') as f:
                                f.write(image_data)
                            
                            # Convert image to markdown
                            image_converter = ImageConverter()
                            image_content, image_metadata = image_converter.convert(temp_path)
                            content.append(image_content)
                            
                            # Clean up temp file
                            temp_path.unlink()
                
                # Extract tables
                tables = page.find_tables()
                if tables:
                    content.append("\n### Tables\n")
                    for table in tables:
                        # Convert table to markdown format
                        rows = table.extract()
                        if rows:
                            # Add table header
                            content.append("| " + " | ".join(str(cell) for cell in rows[0]) + " |")
                            content.append("|" + "|".join("---" for _ in rows[0]) + "|")
                            
                            # Add table rows
                            for row in rows[1:]:
                                content.append("| " + " | ".join(str(cell) for cell in row) + " |")
                            content.append("")
            
            return "\n".join(content), metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert PDF document {file_path}: {str(e)}")
            raise ProcessingError(f"PDF conversion failed: {str(e)}") from e

class ImageConverter(BaseContentConverter):
    """Converts image files to markdown with descriptions."""
    
    def __init__(self, vision_api_key: Optional[str] = None):
        """Initialize image converter.

        Args:
            vision_api_key: Optional OpenAI Vision API key for image descriptions
        """
        super().__init__()
        self.vision_api_key = vision_api_key

    def convert(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Convert image to markdown with description.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Tuple of (markdown content, metadata dict)
        """
        try:
            from PIL import Image
            import openai
            
            # Open image
            img = Image.open(file_path)
            
            # Extract metadata
            metadata = {
                'original_format': img.format.lower(),
                'size': os.path.getsize(file_path),
                'dimensions': f"{img.width}x{img.height}",
                'mode': img.mode,
                'dpi': img.info.get('dpi', 'Unknown')
            }
            
            # Default description
            description = "No AI description available"
            
            # Generate description using OpenAI Vision if available
            if self.vision_api_key:
                try:
                    openai.api_key = self.vision_api_key
                    
                    # Encode image to base64
                    import base64
                    from io import BytesIO
                    
                    # Convert to RGB if needed
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                        
                    # Save to bytes
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    # Call OpenAI Vision API
                    response = openai.ChatCompletion.create(
                        model="gpt-4-vision-preview",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Please describe this image in detail."},
                                    {
                                        "type": "image_url",
                                        "image_url": f"data:image/jpeg;base64,{img_str}"
                                    }
                                ]
                            }
                        ],
                        max_tokens=300
                    )
                    
                    description = response.choices[0].message.content
                    metadata['ai_description'] = description
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate AI description: {str(e)}")
            
            # Convert to markdown
            content = []
            
            # Add image reference
            content.append(f"![{file_path.name}]({file_path})")
            
            # Add description
            content.append(f"\n**Description:** {description}")
            
            # Add technical details
            content.append("\n**Technical Details:**")
            content.append(f"- Format: {metadata['original_format']}")
            content.append(f"- Dimensions: {metadata['dimensions']}")
            content.append(f"- Mode: {metadata['mode']}")
            content.append(f"- DPI: {metadata['dpi']}")
            content.append(f"- Size: {metadata['size']} bytes")
            
            return "\n".join(content), metadata
            
        except Exception as e:
            self.logger.error(f"Failed to convert image file {file_path}: {str(e)}")
            raise ProcessingError(f"Image conversion failed: {str(e)}") from e

# Register converters
ContentConverterFactory.register('html', HTMLConverter)
ContentConverterFactory.register('htm', HTMLConverter)
ContentConverterFactory.register('csv', CSVConverter)
ContentConverterFactory.register('json', JSONConverter)
ContentConverterFactory.register('txt', TextConverter)
ContentConverterFactory.register('text', TextConverter)
ContentConverterFactory.register('md', TextConverter)
ContentConverterFactory.register('markdown', TextConverter)
ContentConverterFactory.register('docx', TextConverter)  # Temporary until proper DOCX converter is implemented
ContentConverterFactory.register('doc', TextConverter)   # Temporary until proper DOC converter is implemented
ContentConverterFactory.register('xlsx', TextConverter)  # Temporary until proper XLSX converter is implemented
ContentConverterFactory.register('xls', TextConverter)   # Temporary until proper XLS converter is implemented
ContentConverterFactory.register('pdf', TextConverter)   # Temporary until proper PDF converter is implemented