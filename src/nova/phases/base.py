"""Base phase interface for Nova document processing."""
import abc
import logging
from pathlib import Path
from typing import Optional, Union

from nova.config.manager import ConfigManager
from nova.models.document import DocumentMetadata


class NovaPhase(abc.ABC):
    """Base class for document processing phases."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize phase.
        
        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Phase name."""
        pass
    
    @abc.abstractmethod
    async def process(
        self,
        file_path: Union[str, Path],
        output_dir: Union[str, Path],
        metadata: Optional[DocumentMetadata] = None,
    ) -> DocumentMetadata:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Output directory for processed files.
            metadata: Optional metadata from previous phase.
        
        Returns:
            Updated document metadata.
        """
        pass 