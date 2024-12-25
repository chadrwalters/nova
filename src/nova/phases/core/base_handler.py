"""Base handler interface for all pipeline phases."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

class BaseHandler(ABC):
    """Base class for all handlers in the pipeline.
    
    This unified base handler combines functionality from parse and consolidate phases,
    providing a consistent interface across the pipeline.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional configuration."""
        self.config = config or {}
    
    @abstractmethod
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Determine if this handler can process the given file and optional attachments.
        
        Args:
            file_path: Path to the main file
            attachments: Optional list of paths to attachments
            
        Returns:
            bool: True if this handler can process the file/attachments
        """
        pass
    
    @abstractmethod
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process the file and optional attachments.
        
        Args:
            file_path: Path to the main file
            context: Additional context for processing
            attachments: Optional list of paths to attachments
            
        Returns:
            Dict containing:
                - content: Processed content
                - processed_attachments: List of processed attachments (if applicable)
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
    
    async def rollback(self, result: Dict[str, Any]) -> None:
        """Rollback any changes if processing fails.
        
        This is optional - handlers can override if they need rollback functionality.
        
        Args:
            result: The processing results to rollback
        """
        pass 