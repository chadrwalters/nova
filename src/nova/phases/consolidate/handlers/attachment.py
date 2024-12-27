"""Handler for processing attachments."""

import os
from pathlib import Path
from typing import Dict, Optional, Set

from ....core.base_handler import BaseHandler
from ....core.console import ConsoleLogger
from ....core.utils.metrics import MetricsTracker
from ....core.utils.timing import TimingManager


class AttachmentHandler(BaseHandler):
    """Handler for processing attachments."""
    
    def __init__(self, config: Optional[Dict] = None, timing: Optional[TimingManager] = None,
                 metrics: Optional[MetricsTracker] = None, console: Optional[ConsoleLogger] = None):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
            timing: Timing manager
            metrics: Metrics tracker
            console: Console logger
        """
        super().__init__(config)
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
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
    
    def process(self, file_path: str, output_dir: str) -> bool:
        """Process the attachment.
        
        Args:
            file_path: Path to the file
            output_dir: Output directory
            
        Returns:
            bool: True if successful
        """
        try:
            with self.timing.measure("process_attachment"):
                src_path = Path(file_path)
                dst_path = Path(output_dir) / src_path.name
                
                # Create output directory if needed
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                os.copy2(src_path, dst_path)
                
                # Update metrics
                self.metrics.increment("attachments_processed")
                self.processed_files.add(file_path)
                
                return True
                
        except Exception as e:
            self.console.error(f"Error processing attachment {file_path}: {e}")
            self.metrics.increment("errors")
            self.failed_files.add(file_path)
            return False 