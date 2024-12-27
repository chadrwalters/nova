"""Base processor for pipeline phases."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rich.console import Console

from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.timing import TimingManager
from nova.core.config.base import ProcessorConfig, PipelineConfig
from nova.core.models.result import ProcessingResult


class BaseProcessor:
    """Base processor for pipeline phases."""
    
    def __init__(
        self,
        processor_config: ProcessorConfig,
        pipeline_config: PipelineConfig,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
            timing: Optional timing utility
            metrics: Optional metrics tracker
            console: Optional console logger
        """
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.console = console or Console()
        
        # Initialize paths
        self.input_dir = Path(processor_config.input_dir or '') if processor_config.input_dir else None
        self.output_dir = Path(processor_config.output_dir) if processor_config.output_dir else None
        self.temp_dir = Path(pipeline_config.temp_dir) if pipeline_config.temp_dir else None
        
        # Initialize state
        self.processed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
        self.skipped_files: Set[str] = set()
        self.errors: List[str] = []
        
        # Initialize handlers
        self.handlers = []
        
    def _initialize(self) -> None:
        """Initialize the processor."""
        # Verify output directory exists
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    async def _process(self, file_path: str) -> None:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
        """
        try:
            # Create context with output directory
            context = {'output_dir': str(self.output_dir)} if self.output_dir else {}
            
            # Check if any handler can process the file
            for handler in self.handlers:
                if await handler.can_handle(file_path):
                    result = await handler.process(file_path, context)
                    if result.success:
                        self.processed_files.add(file_path)
                        self.metrics.increment('files_processed')
                        self.console.print(f"[green]Handler {handler.__class__.__name__} successfully processed file: {file_path}[/green]")
                        return
                    else:
                        self.failed_files.add(file_path)
                        self.errors.extend(result.errors)
                        error_msg = f"Handler {handler.__class__.__name__} failed to process file: {file_path}"
                        self.console.print(f"[red]{error_msg}[/red]")
                        return
                else:
                    self.console.print(f"[yellow]Handler {handler.__class__.__name__} cannot handle file: {file_path}[/yellow]")
                    
            # No handler could process the file
            self.skipped_files.add(file_path)
            warning_msg = f"No handlers could process file: {file_path}"
            self.console.print(f"[yellow]{warning_msg}[/yellow]")
            
        except Exception as e:
            self.failed_files.add(file_path)
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.console.print(f"[red]{error_msg}[/red]")
            
    def _cleanup(self) -> None:
        """Clean up resources."""
        pass
        
    async def process(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        Args:
            file_path: Path to the file to process
            context: Optional context dictionary
            
        Returns:
            ProcessingResult containing processing results
        """
        try:
            # Initialize processor
            self._initialize()
            
            # Process file
            await self._process(file_path)
            
            # Clean up
            self._cleanup()
            
            # Create result
            result = ProcessingResult(
                success=len(self.errors) == 0,
                processed_files=[Path(p) for p in self.processed_files],
                errors=self.errors
            )
            
            # Add failed and skipped files to metadata
            result.metadata.update({
                'failed_files': list(self.failed_files),
                'skipped_files': list(self.skipped_files)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.console.print(f"[red]{error_msg}[/red]")
            return ProcessingResult(
                success=False,
                errors=self.errors,
                metadata={
                    'processed_files': list(self.processed_files),
                    'failed_files': list(self.failed_files),
                    'skipped_files': list(self.skipped_files)
                }
            )
