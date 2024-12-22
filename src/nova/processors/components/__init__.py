"""Component base classes for Nova processors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

from ...core.config import NovaConfig, ProcessorConfig

class ProcessorComponent(ABC):
    """Base class for all processor components."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize component.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        self.config = processor_config
        self.nova_config = nova_config
        self.stats = {
            'errors': 0,
            'warnings': 0,
            'files_processed': 0
        }

class MarkdownComponent(ProcessorComponent):
    """Base class for markdown processing components."""
    
    @abstractmethod
    def process_markdown(self, content: str, source_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content to process
            source_path: Path to source file
            
        Returns:
            Processed markdown content
        """
        pass

class ImageComponent(ProcessorComponent):
    """Base class for image processing components."""
    
    @abstractmethod
    def process_image(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            input_path: Path to input image
            output_path: Path to output image
            
        Returns:
            Dictionary containing image metadata
        """
        pass

class DocumentComponent(ProcessorComponent):
    """Base class for document processing components."""
    
    @abstractmethod
    def process_document(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            input_path: Path to input document
            output_path: Path to output document
            
        Returns:
            Dictionary containing document metadata
        """
        pass 