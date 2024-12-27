"""Office file handler."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import asyncio
from rich.console import Console

from nova.core.errors import HandlerError
from nova.core.logging import get_logger
from nova.core.handlers.base import BaseHandler
from nova.core.utils.timing import TimingManager
from nova.core.utils.metrics import MetricsTracker

logger = get_logger(__name__)

class OfficeHandler(BaseHandler):
    """Handler for office files."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional rich console instance
        """
        super().__init__(
            config=config,
            timing=timing,
            metrics=metrics,
            console=console
        )
        
        # Initialize state
        self.state = {
            "status": "initialized",
            "current_file": None,
            "processed_files": [],
            "failed_files": [],
            "error": None
        }
        
        # Create event loop for async operations
        self._loop = None
    
    async def process(self, input_file: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process an office file.
        
        Args:
            input_file: Path to the file to process
            context: Processing context
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Update state
            self.state["status"] = "running"
            self.state["current_file"] = input_file
            
            # Start timing
            self.metrics.start_timer(f"process_file_{input_file.name}")
            
            # Process file
            processed_content = await self._process_file(input_file)
            
            # Stop timing and update metrics
            self.metrics.stop_timer(f"process_file_{input_file.name}")
            self.metrics.increment("files_processed")
            self.metrics.set_gauge("content_length", len(processed_content), labels={"file": input_file.name})
            
            # Update state
            self.state["processed_files"].append(input_file)
            
            return {
                "success": True,
                "content": processed_content
            }
                
        except Exception as e:
            # Update state
            self.state["status"] = "failed"
            self.state["error"] = str(e)
            self.state["failed_files"].append(input_file)
            
            # Update metrics
            self.metrics.increment("files_failed")
            
            self.error(f"Failed to process file {input_file}: {e}")
            return {
                "success": False,
                "errors": [str(e)]
            }
    
    async def _process_file(self, input_file: Path) -> str:
        """Process an office file.
        
        Args:
            input_file: Path to the file to process
            
        Returns:
            Processed content as markdown
        """
        # TODO: Add actual office file processing
        # For now, just return a placeholder
        return f"# {input_file.stem}\n\nTODO: Process office file {input_file.name}"
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf']
    
    async def validate(self, file_path: Path) -> bool:
        """Validate an office file before processing.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check if file exists
            if not file_path.exists():
                self.error(f"File does not exist: {file_path}")
                return False
                
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                self.error(f"File is not readable: {file_path}")
                return False
                
            # Check file extension
            if not file_path.suffix.lower() in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf']:
                self.error(f"Invalid file extension: {file_path}")
                return False
                
            return True
            
        except Exception as e:
            self.error(f"Failed to validate file {file_path}: {e}")
            return False
    
    def info(self, message: str):
        """Log info message.
        
        Args:
            message: Message to log
        """
        logger.info(message)
        self.console.print(f"[blue]{message}[/blue]")
    
    def warning(self, message: str):
        """Log warning message.
        
        Args:
            message: Message to log
        """
        logger.warning(message)
        self.console.print(f"[yellow]{message}[/yellow]")
    
    def error(self, message: str):
        """Log error message.
        
        Args:
            message: Message to log
        """
        logger.error(message)
        self.console.print(f"[red]{message}[/red]")
    
    def debug(self, message: str):
        """Log debug message.
        
        Args:
            message: Message to log
        """
        logger.debug(message)
        self.console.print(f"[dim]{message}[/dim]")
    
    async def __aenter__(self) -> 'OfficeHandler':
        """Enter async context."""
        # Create event loop if needed
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._loop is not None:
            self._loop.close()
            self._loop = None 