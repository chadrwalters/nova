"""Handler for consolidating markdown files."""

# Standard library imports
import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
from rich.console import Console

# Nova package imports
from nova.core.base_handler import BaseHandler
from nova.core.models.result import ProcessingResult


class ConsolidationHandler(BaseHandler):
    """Handler for consolidating markdown files."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Configuration dictionary
            console: Optional console instance
        """
        super().__init__(config=config, console=console)
        
        # Get required configuration
        if not config:
            raise ValueError("Configuration must be provided")
            
        # Get pipeline and processor configs
        self.pipeline_config = config.get('pipeline_config', {})
        self.processor_config = config.get('processor_config', {})
        
        # Get required paths
        self.input_dir = str(Path(config.get('input_dir', '')))
        self.output_dir = str(Path(config.get('output_dir', '')))
        self.base_dir = str(Path(config.get('base_dir', '')))
        
        if not self.input_dir or not self.output_dir:
            raise ValueError("input_dir and output_dir must be specified in configuration")
    
    async def initialize(self) -> None:
        """Initialize the handler."""
        await super().initialize()
        
        # Validate output directory exists
        if not Path(self.output_dir).exists():
            raise ValueError(f"Output directory does not exist: {self.output_dir}")
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file
            context: Processing context
            
        Returns:
            Processing result
        """
        try:
            # Initialize result
            result = ProcessingResult()
            result.input_file = file_path
            result.output_dir = Path(context.get('output_dir', self.output_dir))
            
            # Process file
            await self._process_impl(file_path, context, result)
            
            # Post-process
            await self._post_process(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)

    async def _process_impl(self, file_path: Path, context: Dict[str, Any], result: ProcessingResult) -> None:
        """Process implementation.
        
        Args:
            file_path: Path to the file
            context: Processing context
            result: Processing result to update
        """
        try:
            # Read content
            content = file_path.read_text()
            
            # Process content
            processed_content = await self._process_content(content)
            
            # Write output
            output_file = result.output_dir / file_path.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(processed_content)
            
            # Update result
            result.success = True
            result.output_files.append(output_file)
            result.content = processed_content
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            result.success = False
            result.errors.append(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)

    async def _process_content(self, content: str) -> str:
        """Process markdown content.
        
        Args:
            content: Content to process
            
        Returns:
            Processed content
        """
        # Process content here
        return content
    
    async def _post_process(self, result: ProcessingResult) -> None:
        """Run post-processing hooks.
        
        Args:
            result: Processing result
        """
        try:
            async with self.monitoring.async_monitor_operation("post_process"):
                for hook in self._post_process_hooks:
                    await hook(result)
        except Exception as e:
            self.monitoring.record_error(f"Error in post-processing: {str(e)}")
    
    async def _on_error(self, error: Exception, result: ProcessingResult) -> None:
        """Run error hooks.
        
        Args:
            error: Exception that occurred
            result: Processing result
        """
        try:
            async with self.monitoring.async_monitor_operation("error_hooks"):
                for hook in self._error_hooks:
                    await hook(error, result)
        except Exception as e:
            self.monitoring.record_error(f"Error in error hooks: {str(e)}")
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def _cleanup_impl(self) -> None:
        """Clean up resources."""
        try:
            async with self.monitoring.async_monitor_operation("cleanup"):
                # Clean up any processed files that had errors
                for file_path in self.processed_files:
                    if file_path.exists() and not self.validate_output(file_path):
                        file_path.unlink()
                        
                        # Clean up attachment directory if it exists
                        attachment_dir = file_path.parent / file_path.stem
                        if attachment_dir.exists():
                            shutil.rmtree(attachment_dir)
        except Exception as e:
            self.monitoring.record_error(f"Error during cleanup: {str(e)}")
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        try:
            async with self.monitoring.async_monitor_operation("rollback"):
                # Clean up any created files
                for file_path in result.processed_files:
                    try:
                        if file_path.exists():
                            file_path.unlink()
                    except Exception as e:
                        error_msg = f"Error cleaning up file {file_path}: {str(e)}"
                        self.monitoring.record_error(error_msg)
                
                # Clean up any created attachment directories
                for file_path in result.processed_files:
                    try:
                        attachment_dir = file_path.parent / file_path.stem
                        if attachment_dir.exists():
                            shutil.rmtree(attachment_dir)
                    except Exception as e:
                        error_msg = f"Error cleaning up attachment directory {attachment_dir}: {str(e)}"
                        self.monitoring.record_error(error_msg)
        except Exception as e:
            self.monitoring.record_error(f"Error during rollback: {str(e)}") 