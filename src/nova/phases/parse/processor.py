"""Processor for parsing markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

from nova.core.errors import ValidationError
from nova.core.config.base import ProcessorConfig
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.core.pipeline.pipeline_state import PipelineState
from nova.phases.core.base_processor import BaseProcessor
from nova.phases.parse.handlers.markdown import MarkdownHandler
from nova.phases.parse.handlers.metadata import MetadataHandler


class MarkdownParseProcessor(BaseProcessor):
    """Processor for parsing markdown files."""

    def __init__(
        self,
        config: ProcessorConfig,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None,
        pipeline_state: Optional[PipelineState] = None
    ):
        """Initialize markdown parse processor.
        
        Args:
            config: Processor configuration
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
            pipeline_state: Optional pipeline state
            
        Raises:
            ValidationError: If configuration is invalid
        """
        super().__init__(
            config=config,
            timing=timing,
            metrics=metrics,
            monitoring=monitoring,
            console=console,
            pipeline_state=pipeline_state
        )
        self.logger = logging.getLogger(__name__)

        # Initialize processor state
        self.processed_files: Set[Path] = set()
        self.failed_files: Set[Path] = set()
        self.skipped_files: Set[Path] = set()
        self.errors: List[str] = []

        # Initialize handlers
        self.handlers = self._initialize_handlers()

    def _initialize_handlers(self) -> List[Any]:
        """Initialize parse handlers.
        
        Returns:
            List of initialized handlers
            
        Raises:
            ValidationError: If handler initialization fails
        """
        handlers = []
        try:
            # Initialize markdown handler
            markdown_handler = MarkdownHandler(
                name="markdown_handler",
                options={
                    'parse_metadata': True,
                    'parse_content': True
                },
                timing=self.timing,
                metrics=self.metrics,
                monitoring=self.monitoring,
                console=self.console
            )
            handlers.append(markdown_handler)

            # Initialize metadata handler
            metadata_handler = MetadataHandler(
                name="metadata_handler",
                options={
                    'extract_metadata': True,
                    'validate_metadata': True
                },
                timing=self.timing,
                metrics=self.metrics,
                monitoring=self.monitoring,
                console=self.console
            )
            handlers.append(metadata_handler)

        except Exception as e:
            raise ValidationError(f"Failed to initialize handlers: {str(e)}")

        return handlers

    async def process(self):
        """Process markdown files.
        
        Raises:
            ValidationError: If processing fails
        """
        try:
            self.logger.info(f"Processing markdown files in {self.input_dir}")

            # Get markdown files
            markdown_files = list(self.input_dir.glob('**/*.md'))
            if not markdown_files:
                self.logger.warning(f"No markdown files found in {self.input_dir}")
                return

            # Process each file
            for file in markdown_files:
                try:
                    self.logger.info(f"Processing file: {file}")
                    
                    # Create output path
                    rel_path = file.name  # Just use filename since files are flat
                    output_file = self.output_dir / rel_path
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    # Process content through handlers
                    for handler in self.handlers:
                        if handler.can_handle(file):
                            result = await handler.process(
                                file_path=file,
                                context={
                                    'output_dir': str(self.output_dir),
                                    'output_file': str(output_file),
                                    'config': self.config
                                }
                            )
                            if not handler.validate_output(result):
                                raise ValidationError(f"Invalid output from handler {handler.get_name()}")

                    # Update state
                    self.processed_files.add(file)
                    self.logger.info(f"File processed successfully: {file}")

                except Exception as e:
                    error_msg = f"Failed to process file {file}: {str(e)}"
                    self.logger.error(error_msg)
                    self.failed_files.add(file)
                    self.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to process markdown files: {str(e)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)

    async def cleanup(self):
        """Clean up processor resources."""
        try:
            # Clean up handlers
            for handler in self.handlers:
                await handler.cleanup()

            # Clean up base processor
            await super().cleanup()

        except Exception as e:
            self.logger.error(f"Error cleaning up processor: {str(e)}")

    def get_handlers(self) -> List[Any]:
        """Get parse handlers.
        
        Returns:
            List of handlers
        """
        return self.handlers

    def get_processed_files(self) -> Set[Path]:
        """Get processed files.
        
        Returns:
            Set of processed file paths
        """
        return self.processed_files

    def get_failed_files(self) -> Set[Path]:
        """Get failed files.
        
        Returns:
            Set of failed file paths
        """
        return self.failed_files

    def get_skipped_files(self) -> Set[Path]:
        """Get skipped files.
        
        Returns:
            Set of skipped file paths
        """
        return self.skipped_files

    def get_errors(self) -> List[str]:
        """Get processing errors.
        
        Returns:
            List of error messages
        """
        return self.errors 