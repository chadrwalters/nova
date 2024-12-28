"""Base handler for processing files."""

# Standard library imports
from pathlib import Path
from typing import Dict, Any, Optional, Set

# Third-party imports
from rich.console import Console

# Nova package imports
from nova.core.models.result import ProcessingResult
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import MetricsTracker, MonitoringManager, TimingManager


class BaseHandler:
    """Base class for file handlers."""
    
    def __init__(self, config: Dict[str, Any], timing: TimingManager,
                 metrics: MetricsTracker, console: Console,
                 pipeline_state: PipelineState,
                 monitoring: Optional[MonitoringManager] = None) -> None:
        """Initialize the handler.
        
        Args:
            config: Handler configuration
            timing: Timing manager instance
            metrics: Metrics tracker instance
            console: Console instance
            pipeline_state: Pipeline state instance
            monitoring: Optional monitoring manager instance
        """
        self.config = config
        self.timing = timing
        self.metrics = metrics
        self.console = console
        self.pipeline_state = pipeline_state
        self.monitoring = monitoring
        
    def can_handle(self, file_path: Path) -> bool:
        """Check if the handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the handler can process the file, False otherwise
        """
        raise NotImplementedError("Subclasses must implement can_handle")
        
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processing results
        """
        raise NotImplementedError("Subclasses must implement process")
        
    def validate_output(self, output_file: Path) -> bool:
        """Validate the output file.
        
        Args:
            output_file: Path to the output file to validate
            
        Returns:
            True if the output file is valid, False otherwise
        """
        raise NotImplementedError("Subclasses must implement validate_output")
        
    async def cleanup(self) -> None:
        """Clean up handler resources."""
        pass 