"""Base processor for handling file processing."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging

from rich.console import Console

from ..utils.metrics import MetricsTracker
from ..utils.timing import TimingManager
from ..models.result import ProcessingResult


class BaseProcessor:
    """Base class for all processors."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the processor.
        
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
        
    async def _initialize(self) -> None:
        """Initialize the processor.
        
        This method should be overridden by subclasses to perform any necessary initialization.
        """
        pass
        
    async def _process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        This method should be overridden by subclasses to implement the actual processing logic.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing the processing results
        """
        raise NotImplementedError("Subclasses must implement _process")
        
    async def _cleanup(self) -> None:
        """Clean up resources.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        pass
        
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        This is the main entry point for processing a file. It handles initialization,
        processing, and cleanup.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing the processing results
        """
        try:
            # Initialize
            await self._initialize()
            
            # Start timing
            self.timing.start_timer(f"process_{file_path.name}")
            
            # Process file
            result = await self._process(file_path, context)
            
            # Stop timing
            duration = self.timing.stop_timer(f"process_{file_path.name}")
            
            # Update metrics
            if result.success:
                self.metrics.increment('files_processed')
            else:
                self.metrics.increment('files_failed')
            self.metrics.add_timing('processing_time', duration)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            return ProcessingResult(success=False, errors=[str(e)])
            
        finally:
            # Clean up
            await self._cleanup() 