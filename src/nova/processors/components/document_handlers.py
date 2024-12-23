"""Document handling components for Nova processors."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from datetime import datetime

from . import DocumentComponent
from ...core.config import NovaConfig, ProcessorConfig
from ...core.errors import ProcessingError
from ...core.logging import get_logger

class OfficeDocumentHandler(DocumentComponent):
    """Handler for office documents. Extracts raw content for MarkitdownHandler to process."""
    
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
            'files_processed': 0,
            'content_extracted': 0
        })
    
    def process_document(self, input_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Process a document.
        
        Args:
            input_path: Path to the document
            output_path: Optional path to save processed document
            
        Returns:
            Dictionary containing processed content and metadata
        """
        return self.extract_content(input_path)
    
    def extract_content(self, input_path: Path) -> Dict[str, Any]:
        """Extract raw content from an office document for MarkitdownHandler to process.
        
        Args:
            input_path: Path to the document
            
        Returns:
            Dictionary containing raw content and metadata
        """
        try:
            # Read raw file content
            with open(input_path, 'rb') as f:
                raw_content = f.read()
            
            # Return raw content and metadata for MarkitdownHandler
            result = {
                'content': raw_content,
                'original_path': str(input_path),
                'file_type': input_path.suffix.lower()[1:],  # Remove leading dot
                'extraction_time': datetime.utcnow().isoformat() + "Z"
            }
            
            self.stats['content_extracted'] += 1
            self.logger.info(f"Extracted content from {input_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {input_path}: {str(e)}")
            raise ProcessingError(f"Content extraction failed: {str(e)}")