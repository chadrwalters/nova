import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from src.processors.converters.base_converter import BaseConverter
from src.core.exceptions import ConversionError

logger = structlog.get_logger(__name__)

class PDFConverter(BaseConverter):
    """Converts PDF documents to markdown."""
    
    async def convert(self, file_path: Path) -> Optional[str]:
        """Convert PDF to markdown text.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Markdown content or None if conversion fails
        """
        try:
            # Open PDF
            doc = fitz.open(file_path)
            
            # Extract text from each page
            content = []
            for page in doc:
                # Get text
                text = page.get_text()
                
                # Basic formatting cleanup
                text = text.replace('\n\n', '\n')  # Remove double line breaks
                
                # Add page marker
                content.append(f"## Page {page.number + 1}\n\n{text}\n")
            
            return '\n'.join(content)
            
        except Exception as e:
            raise ConversionError(
                f"Failed to convert PDF: {str(e)}",
                details={'file': str(file_path)}
            )
        
        finally:
            if 'doc' in locals():
                doc.close()
    
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get PDF metadata.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        try:
            doc = fitz.open(file_path)
            
            metadata = {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'keywords': doc.metadata.get('keywords', ''),
                'created': doc.metadata.get('creationDate', ''),
                'modified': doc.metadata.get('modDate', ''),
                'page_count': doc.page_count,
                'file_size': file_path.stat().st_size
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(
                "Failed to get PDF metadata",
                error=str(e),
                file=str(file_path)
            )
            return {}
            
        finally:
            if 'doc' in locals():
                doc.close() 