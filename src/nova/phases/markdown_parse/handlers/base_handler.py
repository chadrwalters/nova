"""Base handler interface for markdown parsing phase."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

class BaseHandler(ABC):
    """Base class for all handlers in the markdown parse phase."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional configuration."""
        self.config = config or {}
    
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Determine if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if this handler can process the file
        """
        pass
    
    @abstractmethod
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the file and return the results.
        
        Args:
            file_path: Path to the file to process
            context: Additional context for processing
            
        Returns:
            Dict containing processing results
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