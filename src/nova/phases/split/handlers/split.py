"""Handler for splitting markdown files."""

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


class SplitHandler(BaseHandler):
    """Handler for splitting markdown files."""
    
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
        
        # Get split config
        self.output_files = config.get('output_files', {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        })
        self.section_markers = config.get('section_markers', {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW NOTES==--',
            'attachments': '--==ATTACHMENTS==--'
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
        """Process a markdown file by splitting it into sections.
        
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
            
            # Split content into sections
            sections = self._split_content(content)
            
            # Create output directory structure
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Write each section
            processed_files = []
            for section_name, section_content in sections.items():
                output_path = output_dir / self.output_files[section_name]
                output_path.write_text(section_content, encoding='utf-8')
                processed_files.append(str(output_path))
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=content,
                processed_files=processed_files
            )
            
            # Log success
            self.logger.info(f"Handler {self.__class__.__name__} successfully processed file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
            
    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into sections based on markers.
        
        Args:
            content: Content to split
            
        Returns:
            Dictionary containing the sections
        """
        sections = {
            'summary': '',
            'raw_notes': '',
            'attachments': ''
        }
        
        current_section = 'summary'
        lines = content.split('\n')
        
        for line in lines:
            if line.strip() == self.section_markers['summary']:
                current_section = 'summary'
                continue
            elif line.strip() == self.section_markers['raw_notes']:
                current_section = 'raw_notes'
                continue
            elif line.strip() == self.section_markers['attachments']:
                current_section = 'attachments'
                continue
                
            sections[current_section] += line + '\n'
            
        return sections 