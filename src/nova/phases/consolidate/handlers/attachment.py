"""Handler for processing attachments."""

# Standard library imports
import os
from pathlib import Path
from typing import Dict, Optional, Set

# Nova package imports
from nova.core.base_handler import BaseHandler
from nova.core.console import ConsoleLogger
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.utils.timing import TimingManager
from nova.core.models.result import HandlerResult


class AttachmentHandler(BaseHandler):
    """Handler for processing attachments."""
    
    def __init__(
        self,
        name: str,
        options: Dict,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize the handler.
        
        Args:
            name: Handler name
            options: Handler options
            timing: Timing manager
            metrics: Metrics tracker
            monitoring: Monitoring manager
            console: Console logger
        """
        super().__init__(name=name, options=options)
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.monitoring = monitoring or MonitoringManager()
        self.console = console or ConsoleLogger()
        self.processed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
    
    def can_handle(self, file_path: str) -> bool:
        """Check if the file can be handled.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file can be handled
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file()
        except Exception as e:
            self.console.error(f"Error checking file {file_path}: {e}")
            return False
    
    async def process(self, file_path: str, context: Dict[str, str]) -> HandlerResult:
        """Process the file.
        
        Args:
            file_path: Path to the file
            context: Processing context containing output_dir
            
        Returns:
            HandlerResult containing processing result
        """
        try:
            # Get output directory from context
            output_dir = context.get('output_dir')
            if not output_dir:
                error_msg = "No output directory specified in context"
                self.logger.error(error_msg)
                return HandlerResult(success=False, errors=[error_msg])
                
            # Process file
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            
            # Skip if not a file
            if not file_path.is_file():
                error_msg = f"Not a file: {file_path}"
                self.logger.warning(error_msg)
                return HandlerResult(success=False, errors=[error_msg])
                
            # Copy file to output directory
            output_file = output_dir / file_path.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                content = src.read()
                dst.write(content)
                
            # Update state
            self.processed_files.add(str(file_path))
            self.logger.info(f"Processed file: {file_path}")
            
            return HandlerResult(
                success=True,
                content=content.decode('utf-8', errors='ignore'),
                metadata={
                    'input_file': str(file_path),
                    'output_file': str(output_file),
                    'size': len(content)
                }
            )
            
        except Exception as e:
            self.failed_files.add(str(file_path))
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            return HandlerResult(success=False, errors=[error_msg])
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate handler output.
        
        Args:
            result: Handler result
            
        Returns:
            True if result is valid, False otherwise
        """
        return (
            isinstance(result, HandlerResult) and
            result.success and
            isinstance(result.content, str) and
            isinstance(result.metadata, dict) and
            'input_file' in result.metadata and
            'output_file' in result.metadata
        ) 