"""Base handler interface for markdown aggregation phase."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List

class BaseAggregateHandler(ABC):
    """Base class for all handlers in the markdown aggregate phase."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional configuration."""
        self.config = config or {}
    
    @abstractmethod
    def can_handle(self, files: List[Path]) -> bool:
        """Determine if this handler can process the given files.
        
        Args:
            files: List of paths to markdown files to aggregate
            
        Returns:
            bool: True if this handler can process the files
        """
        pass
    
    @abstractmethod
    async def process(self, files: List[Path], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and aggregate the files.
        
        Args:
            files: List of paths to markdown files to aggregate
            context: Additional context for processing
            
        Returns:
            Dict containing:
                - content: Aggregated markdown content
                - metadata: Combined metadata
                - file_map: Mapping of original files to sections
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