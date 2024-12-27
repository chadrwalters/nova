"""Handler for consolidating markdown files."""

from pathlib import Path
from typing import Any, Dict, Optional
import asyncio
import shutil
import os
from rich.console import Console

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
            config: Handler configuration
            console: Optional rich console instance
        """
        super().__init__(config=config, console=console)
        
        # Get required configuration
        if not config:
            raise ValueError("Configuration must be provided")
            
        # Get pipeline and processor configs
        self.pipeline_config = config.get('pipeline_config', {})
        self.processor_config = config.get('processor_config', {})
        
        # Get handler config
        self.handler_config = config.get('config', {})
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def _process_impl(self, file_path: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            
        Returns:
            ProcessingResult: Processing results
        """
        try:
            async with self.monitoring.async_monitor_operation("read_file"):
                # Read input file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            async with self.monitoring.async_monitor_operation("consolidate_content"):
                # Process the content (placeholder for actual consolidation)
                processed_content = content
                
                # Get output directory
                output_dir = None
                if context and 'output_dir' in context:
                    output_dir = Path(context['output_dir'])
                elif self.config and 'output_dir' in self.config:
                    output_dir = Path(self.config['output_dir'])
                
                if not output_dir:
                    error_msg = "No output directory specified"
                    self.monitoring.record_error(error_msg)
                    return ProcessingResult(success=False, errors=[error_msg])
            
            async with self.monitoring.async_monitor_operation("write_output"):
                # Create output directory if it doesn't exist
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create output file
                output_file = output_dir / file_path.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
                
                # Create result
                result = ProcessingResult(
                    success=True,
                    content=processed_content,
                    metadata={
                        'input_file': str(file_path),
                        'output_file': str(output_file)
                    }
                )
                result.add_processed_file(file_path)
                result.add_processed_file(output_file)
                
                # Record success metrics
                self.monitoring.increment_counter("files_processed")
                
                return result
                
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            self.monitoring.record_error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
    
    async def _cleanup_impl(self) -> None:
        """Clean up resources."""
        pass 