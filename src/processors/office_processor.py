"""Office document processor for converting documents to markdown format."""

import os
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, Any

from markitdown import MarkItDown
from markitdown._markitdown import FileConversionException, UnsupportedFormatException

from ..core.errors import ProcessingError
from ..core.logging import get_logger

logger = get_logger(__name__)

class OfficeProcessor:
    """Handles conversion of office documents to markdown."""
    
    def __init__(self):
        """Initialize the office processor."""
        self.converter = MarkItDown()
        self.stats = {
            'documents_processed': 0,
            'conversion_errors': 0,
            'total_size': 0
        }
    
    def process_document(self, input_path: Path, output_dir: Path) -> str:
        """Process an office document and return markdown content."""
        try:
            # Convert the document
            result = self.converter.convert(
                str(input_path),
                image_dir=str(output_dir),
                extract_images=True,
                preserve_formatting=True
            )
            
            # Extract content and metadata
            content = self._extract_content(result)
            metadata = self._create_metadata(input_path, result)
            
            # Format the output
            return self._format_output(input_path, content, metadata, result)
            
        except Exception as e:
            logger.error(f"Failed to process document {input_path.name}: {e}")
            self.stats['conversion_errors'] += 1
            raise ProcessingError(f"Document conversion failed: {str(e)}")
    
    def _extract_content(self, result: Any) -> str:
        """Extract content from the converter result."""
        # Try different ways to get content
        if hasattr(result, 'text_content'):
            return result.text_content
        elif hasattr(result, 'markdown'):
            return result.markdown
        elif hasattr(result, 'text'):
            return result.text
        elif hasattr(result, '__dict__') and 'text_content' in result.__dict__:
            return result.__dict__['text_content']
        
        # Log failure details
        logger.error(f"Could not extract content. Type: {type(result)}, Attributes: {dir(result)}")
        return None
    
    def _create_metadata(self, input_path: Path, result: Any) -> Dict[str, Any]:
        """Create metadata for the document."""
        metadata = {
            'source_file': input_path.name,
            'original_size': input_path.stat().st_size,
            'processed_date': datetime.now().isoformat(),
            'file_type': input_path.suffix[1:].upper()
        }
        
        if hasattr(result, 'title') and result.title:
            metadata['title'] = result.title
            
        return metadata
    
    def _format_output(self, input_path: Path, content: Optional[str], metadata: Dict[str, Any], result: Any) -> str:
        """Format the final markdown output."""
        # Create the header
        header = "---\n" + "\n".join(f"{k}: {v}" for k, v in metadata.items()) + "\n---\n\n"
        
        # Format the content sections
        sections = [f"# {metadata.get('title', input_path.name)}\n"]
        
        if content and content.strip() and content.strip() != str(result):
            sections.append(content)
        else:
            sections.extend([
                "Content could not be extracted properly. Please refer to the original document.",
                "",
                "## Technical Details",
                f"Converter returned: {type(result)}",
                f"Available attributes: {', '.join(dir(result))}",
                f"Result dict: {result.__dict__ if hasattr(result, '__dict__') else 'No __dict__'}"
            ])
        
        sections.extend([
            "",
            "## Document Information",
            f"- File: {input_path.name}",
            f"- Type: {input_path.suffix[1:].upper()}",
            f"- Size: {input_path.stat().st_size / 1024:.1f} KB"
        ])
        
        return header + "\n".join(sections) 