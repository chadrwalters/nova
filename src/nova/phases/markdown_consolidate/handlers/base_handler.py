"""Base handler interface for markdown consolidation phase."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List

class BaseConsolidateHandler(ABC):
    """Base class for all handlers in the markdown consolidate phase."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional configuration."""
        self.config = config or {}
    
    @abstractmethod
    def can_handle(self, file_path: Path, attachments: List[Path]) -> bool:
        """Determine if this handler can process the given file and attachments.
        
        Args:
            file_path: Path to the main markdown file
            attachments: List of paths to potential attachments
            
        Returns:
            bool: True if this handler can process the file and attachments
        """
        pass
    
    @abstractmethod
    async def process(self, file_path: Path, attachments: List[Path], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the file and its attachments.
        
        Args:
            file_path: Path to the main markdown file
            attachments: List of paths to attachments
            context: Additional context for processing
            
        Returns:
            Dict containing:
                - content: Consolidated markdown content
                - processed_attachments: List of processed attachments
                - metadata: Combined metadata
                - errors: List of processing errors
        """
        pass
    
    @abstractmethod
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate the processing results.
        
        Args:
            result: The processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        pass
    
    @abstractmethod
    async def rollback(self, result: Dict[str, Any]) -> None:
        """Rollback any changes if processing fails.
        
        Args:
            result: The processing results to rollback
        """
        pass 