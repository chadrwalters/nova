"""Handler for processing markdown content."""

import os
from pathlib import Path
from typing import Dict, Optional, Set

from ....core.base_handler import BaseHandler
from ....core.console import Console
from ....core.utils.metrics import MetricsTracker
from ....core.utils.timing import TimingManager


class ContentHandler(BaseHandler):
    """Handler for processing markdown content."""
    
    def __init__(self, config: Optional[Dict] = None, timing: Optional[TimingManager] = None,
                 metrics: Optional[MetricsTracker] = None, console: Optional[Console] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
            timing: Optional timing utility
            metrics: Optional metrics tracker
            console: Optional console logger
        """
        super().__init__(config, timing, metrics, console)
        self.processed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
        self.skipped_files: Set[str] = set()
        
    def can_handle(self, file_path: str) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.endswith('.md')
        
    def process(self, file_path: str, output_dir: str) -> bool:
        """Process a file.
        
        Args:
            file_path: Path to the file to process
            output_dir: Directory to write output to
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Get output path
            file_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, file_name)
            
            # Copy file
            with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
                
            self.processed_files.add(file_path)
            self.metrics.increment('files_processed')
            self.console.info(f"Handler {self.__class__.__name__} successfully processed file: {file_path}")
            return True
            
        except Exception as e:
            self.failed_files.add(file_path)
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.console.error(error_msg)
            return False 