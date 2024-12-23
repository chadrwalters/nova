"""Office document processor for Nova."""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from ..core.base import BaseProcessor
from ..core.config import NovaConfig, ProcessorConfig
from ..core.logging import get_logger
from .components.document_handlers import OfficeDocumentHandler
from .components.markdown_handlers import MarkitdownHandler

class OfficeProcessor(BaseProcessor):
    """Processor for office documents."""
    
    def _setup(self) -> None:
        """Setup office processor requirements."""
        self.office_handler = OfficeDocumentHandler(
            processor_config=self.config,
            nova_config=self.nova_config
        )
        
        self.markdown_handler = MarkitdownHandler(
            processor_config=self.config,
            nova_config=self.nova_config
        )
    
    def process(self, input_path: Path) -> Path:
        """Process an office document.
        
        Args:
            input_path: Path to the office document
            
        Returns:
            Path to the processed document
        """
        # Extract raw content using office handler
        extracted_data = self.office_handler.extract_content(input_path)
        
        # Determine output path
        output_path = Path(self.nova_config.paths.output_dir) / input_path.relative_to(Path(self.nova_config.paths.input_dir))
        output_path = output_path.with_suffix('.md')
        
        # Process content using markdown handler
        processed_content = self.markdown_handler.process_content(
            content=extracted_data['content'],
            metadata={
                'original_path': extracted_data['original_path'],
                'file_type': extracted_data['file_type'],
                'extraction_time': extracted_data['extraction_time']
            },
            output_path=output_path
        )
        
        # Save metadata
        metadata_path = output_path.with_suffix('.json')
        self._cache_result(str(metadata_path), processed_content['metadata'])
        
        return output_path