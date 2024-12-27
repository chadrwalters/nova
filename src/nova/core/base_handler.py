"""Base handler for file processing."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging

from rich.console import Console

from .utils.metrics import MetricsTracker
from .utils.timing import TimingManager
from .models.result import ProcessingResult


class BaseHandler:
    """Base class for all handlers."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional rich console instance
        """
        self.config = config or {}
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.console = console or Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def initialize(self) -> None:
        """Initialize the handler.
        
        This method should be overridden by subclasses to perform any necessary initialization.
        """
        pass
        
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
        This method should be overridden by subclasses to implement the actual check logic.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        raise NotImplementedError("Subclasses must implement can_handle")
        
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        This method should be overridden by subclasses to implement the actual processing logic.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing the processing results
        """
        raise NotImplementedError("Subclasses must implement process")
        
    async def cleanup(self) -> None:
        """Clean up resources.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        pass 