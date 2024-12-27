"""Base handler for processing phases."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import functools

from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.console.logger import ConsoleLogger
from nova.core.models.result import ProcessingResult
from nova.core.utils.timing import TimingManager


@dataclass
class HandlerConfig:
    """Configuration for a handler."""
    type: str
    base_handler: str
    options: Dict[str, Any] = field(default_factory=dict)
    document_conversion: bool = False
    image_processing: bool = False
    metadata_preservation: bool = False
    sort_by_date: bool = False
    preserve_headers: bool = False
    copy_attachments: bool = False
    update_references: bool = False
    merge_content: bool = False
    section_markers: Optional[Dict[str, str]] = None
    link_style: Optional[str] = None
    position: Optional[str] = None
    add_top_link: bool = False
    templates: Optional[Dict[str, Any]] = None


class BaseHandler:
    """Base class for all handlers."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional console logger instance
        """
        self.config = config or {}
        self.metrics = metrics or MetricsTracker()
        self.timing = timing or TimingManager()
        self.console = console or ConsoleLogger()
        self.monitor = MonitoringManager()
        self.error_tracker = ErrorTracker()
        
        # Initialize state
        self.state = {
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': []
        }
        
        # Create event loop for async operations
        self._loop = None
        
        # Set up input/output directories
        self.input_dir = Path(self.config.get('input_dir', ''))
        self.output_dir = Path(self.config.get('output_dir', ''))
        self.base_dir = Path(self.config.get('base_dir', ''))

    def get_output_path(self, relative_path: Union[str, Path]) -> Path:
        """Get the output path for a file.
        
        Args:
            relative_path: Path relative to the input directory
            
        Returns:
            Full output path
        """
        relative_path = Path(relative_path)
        return self.output_dir / relative_path
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult with processing results
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return False
    
    def _validate(self, file_path: Path) -> bool:
        """Validate a file before processing.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        return True
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        try:
            # Run synchronous method in executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._can_handle, file_path)
            return bool(result)
        except Exception:
            return False
    
    async def validate(self, file_path: Path) -> bool:
        """Validate a file before processing.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Run synchronous method in executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._validate, file_path)
            return bool(result)
        except Exception:
            return False
    
    async def cleanup(self) -> None:
        """Clean up any resources used by the handler."""
        pass
    
    async def __aenter__(self) -> 'BaseHandler':
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