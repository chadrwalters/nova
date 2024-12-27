"""Handler for parsing markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import os
import shutil

from rich.console import Console

from ....core.base_handler import BaseHandler
from ....core.utils.metrics import MetricsTracker
from ....core.utils.timing import TimingManager
from ....core.models.result import ProcessingResult


class MarkdownHandler(BaseHandler):
    """Handler for parsing markdown files."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional rich console instance
        """
        super().__init__(config, timing, metrics, console)
        
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
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
            ProcessingResult containing the processing results
        """
        try:
            # Get output directory from context
            if not context or 'output_dir' not in context:
                error_msg = "No output directory specified in context"
                self.logger.error(error_msg)
                return ProcessingResult(success=False, errors=[error_msg])
                
            output_dir = context['output_dir']
            
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            
            # Create output directory structure
            relative_path = file_path.relative_to(Path(os.environ.get('NOVA_INPUT_DIR', '')))
            output_path = Path(output_dir) / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write processed content
            output_path.write_text(content, encoding='utf-8')
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=content,
                processed_files=[str(output_path)]
            )
            
            # Log success
            self.logger.info(f"Handler {self.__class__.__name__} successfully processed file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg]) 