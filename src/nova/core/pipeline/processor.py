"""Base processor for pipeline phases."""

# Standard library imports
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
from rich.console import Console

# Nova package imports
from nova.core.config.base import PipelineConfig, ProcessorConfig
from nova.core.pipeline.base import BaseProcessor
from nova.core.utils.metrics import MetricsTracker, MonitoringManager, TimingManager

from ..utils.metrics import MetricsTracker
from ..utils.metrics import MonitoringManager
from ..utils.metrics import TimingManager
from ..config.base import ProcessorConfig

from .base import BaseProcessor


class PipelineProcessor(BaseProcessor):
    """Base class for pipeline processors."""
    
    def __init__(
        self,
        processor_config: ProcessorConfig,
        pipeline_config: PipelineConfig,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None,
        monitoring: Optional[MonitoringManager] = None
    ):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
            timing: Optional timing utility
            metrics: Optional metrics tracker
            console: Optional console logger
            monitoring: Optional monitoring manager
        """
        super().__init__(processor_config, pipeline_config, timing, metrics, console)
        self.monitoring = monitoring or MonitoringManager()
        
    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> None:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
        """
        try:
            # Create context with output directory
            context = context or {}
            if self.output_dir:
                context['output_dir'] = str(self.output_dir)
            
            # Check if any handler can process the file
            for handler in self.handlers:
                if await handler.can_handle(file_path):
                    result = await handler.process(file_path, context)
                    if result.success:
                        self.processed_files.add(str(file_path))
                        self.metrics.increment('files_processed')
                        if self.monitoring:
                            self.monitoring.increment_counter('files_processed')
                        self.console.print(f"[green]Handler {handler.__class__.__name__} successfully processed file: {file_path}[/green]")
                        return
                    else:
                        self.failed_files.add(str(file_path))
                        self.errors.extend(result.errors)
                        error_msg = f"Handler {handler.__class__.__name__} failed to process file: {file_path}"
                        self.console.print(f"[red]{error_msg}[/red]")
                        if self.monitoring:
                            self.monitoring.record_error(error_msg)
                        return
                else:
                    self.console.print(f"[yellow]Handler {handler.__class__.__name__} cannot handle file: {file_path}[/yellow]")
                    
            # No handler could process the file
            self.skipped_files.add(str(file_path))
            warning_msg = f"No handlers could process file: {file_path}"
            self.console.print(f"[yellow]{warning_msg}[/yellow]")
            if self.monitoring:
                self.monitoring.increment_counter('files_skipped')
            
        except Exception as e:
            self.failed_files.add(str(file_path))
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.console.print(f"[red]{error_msg}[/red]")
            if self.monitoring:
                self.monitoring.record_error(error_msg)
    
    async def process_files(self, file_paths: List[Path]) -> None:
        """Process multiple files.
        
        Args:
            file_paths: List of file paths to process
        """
        if self.monitoring:
            self.monitoring.start()
            
        try:
            # Initialize processor
            self._initialize()
            
            # Process each file
            for file_path in file_paths:
                await self._process_impl(file_path)
                
            # Clean up
            self._cleanup()
            
        finally:
            if self.monitoring:
                self.monitoring.stop()
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        # Clean up base resources
        self._cleanup()
        
        # Clean up monitoring
        if self.monitoring:
            self.monitoring.cleanup()
        
        # Clean up handlers
        for handler in self.handlers:
            if hasattr(handler, 'cleanup'):
                await handler.cleanup()