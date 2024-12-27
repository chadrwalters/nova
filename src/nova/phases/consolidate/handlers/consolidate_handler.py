"""Handler for consolidating markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import shutil
import os

from ....core.handlers.base import BaseHandler
from ....core.utils.metrics import MetricsTracker
from ....core.utils.monitoring import MonitoringManager
from ....core.utils.error_tracker import ErrorTracker
from ....core.console.logger import ConsoleLogger
from ....core.models.result import ProcessingResult


class ConsolidateHandler(BaseHandler):
    """Handler for consolidating markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.metrics = MetricsTracker()
        self.monitor = MonitoringManager()
        self.error_tracker = ErrorTracker()
        self.logger = ConsoleLogger()
        
        # Get required configuration
        if not config:
            raise ValueError("Configuration must be provided")
            
        # Get pipeline and processor configs
        self.pipeline_config = config.get('pipeline_config', {})
        self.processor_config = config.get('processor_config', {})
        
        # Get handler config
        handler_config = config.get('config', {})
        
        # Get required paths
        self.input_dir = str(Path(config.get('input_dir', '')))
        self.output_dir = str(Path(config.get('output_dir', '')))
        self.base_dir = str(Path(config.get('base_dir', '')))
        
        if not self.input_dir or not self.output_dir:
            raise ValueError("input_dir and output_dir must be specified in configuration")
        
        # Initialize state
        self.state = {
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': []
        }
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processed content and metadata
        """
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Use configured output directory
            output_dir = Path(self.output_dir)
            
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Read input file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create attachment directory
            attachment_dir = output_dir / file_path.stem
            os.makedirs(attachment_dir, exist_ok=True)
            
            # Process attachments if they exist
            attachments = []
            input_attachment_dir = file_path.parent / file_path.stem
            
            if input_attachment_dir.exists():
                self.logger.info(f"Found attachment directory: {input_attachment_dir}")
                
                # Process attachments
                for attachment in input_attachment_dir.iterdir():
                    if attachment.is_file():
                        dest_path = attachment_dir / attachment.name
                        shutil.copy2(attachment, dest_path)
                        attachments.append(dest_path)
            
            self.logger.info(f"Handler {self.__class__.__name__} successfully processed file: {file_path}")
            result = ProcessingResult(
                success=True,
                content=content,
                attachments=attachments
            )
            result.add_processed_file(file_path)
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
    
    async def _post_process(self, result: ProcessingResult) -> None:
        """Run post-processing hooks.
        
        Args:
            result: Processing result
        """
        for hook in self._post_process_hooks:
            await hook(result)
    
    async def _on_error(self, error: Exception, result: ProcessingResult) -> None:
        """Run error hooks.
        
        Args:
            error: Exception that occurred
            result: Processing result
        """
        for hook in self._error_hooks:
            await hook(error, result)
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        # Clean up any created files
        for file_path in result.processed_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                self.logger.error(f"Error cleaning up file {file_path}: {str(e)}")
        
        # Clean up any created attachment directories
        for file_path in result.processed_files:
            try:
                attachment_dir = file_path.parent / file_path.stem
                if attachment_dir.exists():
                    shutil.rmtree(attachment_dir)
            except Exception as e:
                self.logger.error(f"Error cleaning up attachment directory {attachment_dir}: {str(e)}") 