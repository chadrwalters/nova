"""Handler for aggregating markdown files."""

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
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.timing import TimingManager


class AggregateHandler(BaseHandler):
    """Handler for aggregating markdown files."""
    
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
        
        # Get section markers from config
        self.section_markers = config.get('section_markers', {
            'start': '<!-- START_FILE: {filename} -->',
            'end': '<!-- END_FILE: {filename} -->',
            'separator': '\n---\n'
        })
        
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
        
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file by aggregating it with others.
        
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
            
            # Add file markers
            header = self.section_markers['start'].format(filename=file_path.name)
            footer = self.section_markers['end'].format(filename=file_path.name)
            separator = self.section_markers['separator']
            
            processed_content = f"{header}\n\n{content}\n\n{footer}{separator}"
            
            # Create output directory structure
            output_path = Path(output_dir) / "all_merged_markdown.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append processed content
            with open(output_path, 'a', encoding='utf-8') as f:
                f.write(processed_content)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=processed_content,
                processed_files=[str(output_path)]
            )
            
            # Log success
            self.logger.info(f"Handler {self.__class__.__name__} successfully processed file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg]) 