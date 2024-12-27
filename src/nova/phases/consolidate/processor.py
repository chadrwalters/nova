"""Processor for consolidating markdown files."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console

from ...core.pipeline.base import BaseProcessor
from ...core.utils.metrics import MetricsTracker
from ...core.utils.timing import TimingManager
from ...core.config import ProcessorConfig, PipelineConfig

from .handlers.attachment import AttachmentHandler
from .handlers.content import ContentHandler


class MarkdownConsolidateProcessor(BaseProcessor):
    """Processor for consolidating markdown files."""
    
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
        super().__init__(processor_config, pipeline_config, timing, metrics, console)
        self.processed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
        self.skipped_files: Set[str] = set()
        self.errors: List[str] = []
        
        # Initialize handlers
        config = {
            'input_dir': self.input_dir,
            'output_dir': self.output_dir,
            'temp_dir': self.temp_dir,
            'options': processor_config.options
        }
        self.handlers = [
            AttachmentHandler(config, timing, metrics, console),
            ContentHandler(config, timing, metrics, console)
        ]
        
    def _initialize(self) -> None:
        """Initialize the processor."""
        # Verify output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def _process(self, file_path: str) -> None:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
        """
        try:
            # Check if any handler can process the file
            for handler in self.handlers:
                if handler.can_handle(file_path):
                    result = handler.process(file_path)
                    if result.success:
                        self.processed_files.add(file_path)
                        self.metrics.increment('files_processed')
                        self.console.info(f"Handler {handler.__class__.__name__} successfully processed file: {file_path}")
                        return
                    else:
                        self.failed_files.add(file_path)
                        self.errors.extend(result.errors)
                        error_msg = f"Handler {handler.__class__.__name__} failed to process file: {file_path}"
                        self.console.error(error_msg)
                        return
                else:
                    self.console.info(f"Handler {handler.__class__.__name__} cannot handle file: {file_path}")
                    
            # No handler could process the file
            self.skipped_files.add(file_path)
            warning_msg = f"No handlers could process file: {file_path}"
            self.console.warning(warning_msg)
            
        except Exception as e:
            self.failed_files.add(file_path)
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.console.error(error_msg)
            
    def _cleanup(self) -> None:
        """Clean up resources."""
        pass