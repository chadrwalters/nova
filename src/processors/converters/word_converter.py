import mammoth
import docx
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import aiofiles
from datetime import datetime

from src.processors.converters.base_converter import BaseConverter
from src.core.exceptions import ConversionError

logger = structlog.get_logger(__name__)

class WordConverter(BaseConverter):
    """Converts Word documents to markdown."""
    
    async def convert(self, file_path: Path) -> Optional[str]:
        """Convert Word document to markdown.
        
        Args:
            file_path: Path to Word document
            
        Returns:
            Markdown content or None if conversion fails
        """
        try:
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Convert to markdown using mammoth
            result = mammoth.convert_to_markdown(content)
            
            # Log any warnings
            if result.messages:
                for msg in result.messages:
                    logger.warning(
                        "Word conversion warning",
                        message=str(msg),
                        file=str(file_path)
                    )
            
            return result.value
            
        except Exception as e:
            raise ConversionError(
                f"Failed to convert Word document: {str(e)}",
                details={'file': str(file_path)}
            )
    
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get Word document metadata.
        
        Args:
            file_path: Path to Word document
            
        Returns:
            Dictionary of metadata
        """
        try:
            doc = docx.Document(file_path)
            core_props = doc.core_properties
            
            return {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'created': core_props.created or datetime.now(),
                'modified': core_props.modified or datetime.now(),
                'last_modified_by': core_props.last_modified_by or '',
                'revision': core_props.revision or 1,
                'word_count': len(doc.paragraphs),
                'page_count': len(doc.sections)
            }
            
        except Exception as e:
            logger.warning(
                "Failed to get Word metadata",
                error=str(e),
                file=str(file_path)
            )
            return {} 