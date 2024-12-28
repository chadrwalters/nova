"""Base handler for file processing."""

# Standard library imports
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
from rich.console import Console

# Nova package imports
from nova.core.models.result import ProcessingResult
from nova.core.models.state import HandlerState
from nova.core.utils.metrics import MetricsTracker, MonitoringManager


class BaseHandler:
    """Base class for all handlers."""
    
    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            name: Handler name
            options: Handler options
            metrics: Optional metrics tracker instance
            monitoring: Optional monitoring manager instance
            console: Optional rich console instance
        """
        self.name = name
        self.options = options
        self.metrics = metrics or MetricsTracker()
        self.monitoring = monitoring or MonitoringManager()
        self.console = console or Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state = HandlerState()
        
    async def initialize(self) -> None:
        """Initialize the handler.
        
        This method should be overridden by subclasses to perform any necessary initialization.
        """
        self.monitoring.start()
        await self.monitoring.async_capture_resource_usage()
        self.state.start()
        
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
        async with self.monitoring.async_monitor_operation(f"process_{self.__class__.__name__}"):
            try:
                # Check output directory before processing
                if not self._check_output_directory():
                    error_msg = "No output directory specified"
                    self.monitoring.record_error(error_msg)
                    return ProcessingResult(success=False, errors=[error_msg])
                
                result = await self._process_impl(file_path, context)
                if not result.success:
                    error_msg = str(result.errors[0]) if result.errors else "Unknown error"
                    self.monitoring.record_error(error_msg)
                    self.state.add_error(error_msg)
                return result
            except Exception as e:
                error_msg = f"Error in {self.__class__.__name__}: {str(e)}"
                self.monitoring.record_error(error_msg)
                self.state.add_error(error_msg)
                return ProcessingResult(success=False, errors=[error_msg])
    
    def _check_output_directory(self) -> bool:
        """Check if output directory is specified.
        
        Returns:
            True if output directory is specified, False otherwise
        """
        return bool(self.options.get("output_dir"))
    
    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Implementation of the process method.
        
        This method should be overridden by subclasses to implement the actual processing logic.
        The base process method handles monitoring and error tracking.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing the processing results
        """
        raise NotImplementedError("Subclasses must implement _process_impl")
        
    async def cleanup(self) -> None:
        """Clean up resources.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        try:
            self.monitoring.stop()
            await self.monitoring.async_capture_resource_usage()
            self.state.end()
        finally:
            await self._cleanup_impl()
    
    async def _cleanup_impl(self) -> None:
        """Implementation of the cleanup method.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        The base cleanup method handles monitoring cleanup.
        """
        pass 