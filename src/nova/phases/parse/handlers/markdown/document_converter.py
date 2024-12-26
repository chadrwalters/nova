"""Document conversion handler for markdown processing."""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import mimetypes
import logging
from dataclasses import dataclass

from nova.core.handlers.content_converters import (
    DocxConverter,
    PptxConverter,
    XlsxConverter,
    PdfConverter,
    CsvConverter,
    HtmlConverter
)
from nova.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ConversionResult:
    """Result of document conversion."""
    content: str
    metadata: Dict[str, Any]
    success: bool
    converter_name: str
    error: Optional[str] = None

class DocumentConverter:
    """Handles conversion of documents to markdown format."""
    
    def __init__(self):
        """Initialize document converter."""
        self.converters = {
            '.docx': DocxConverter(),
            '.doc': DocxConverter(),
            '.pptx': PptxConverter(),
            '.ppt': PptxConverter(),
            '.xlsx': XlsxConverter(),
            '.xls': XlsxConverter(),
            '.pdf': PdfConverter(),
            '.csv': CsvConverter(),
            '.html': HtmlConverter()
        }
        
        # Initialize mimetypes
        mimetypes.init()
        mimetypes.add_type('application/pdf', '.pdf')
        mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
        mimetypes.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')
        mimetypes.add_type('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
        mimetypes.add_type('text/html', '.html')
    
    async def convert_to_markdown(self, file_path: Path, output_dir: Path) -> ConversionResult:
        """Convert a document to markdown format.
        
        Args:
            file_path: Path to the document to convert
            output_dir: Directory to save any extracted resources
            
        Returns:
            ConversionResult containing the markdown content and metadata
        """
        try:
            # Get file extension and mimetype
            ext = file_path.suffix.lower()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Get appropriate converter
            converter = self.converters.get(ext)
            if not converter:
                return ConversionResult(
                    content='',
                    metadata={'type': mime_type or 'application/octet-stream'},
                    success=False,
                    converter_name='',
                    error=f"No converter available for {ext} files"
                )
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy original file to output directory
            output_file = output_dir / file_path.name
            shutil.copy2(file_path, output_file)
            
            # Convert document
            logger.info(f"Converting {file_path} to markdown")
            content = await converter.convert(file_path)
            
            # Create metadata
            metadata = {
                'type': mime_type or 'application/octet-stream',
                'original_file': file_path.name,
                'converter': converter.__class__.__name__
            }
            
            return ConversionResult(
                content=content,
                metadata=metadata,
                success=True,
                converter_name=converter.__class__.__name__
            )
            
        except Exception as e:
            error = f"Failed to convert {file_path}: {str(e)}"
            logger.error(error)
            return ConversionResult(
                content='',
                metadata={'type': 'unknown'},
                success=False,
                converter_name='',
                error=error
            ) 