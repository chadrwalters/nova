"""Handler for adding navigation to markdown files."""

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


class NavigationHandler(BaseHandler):
    """Handler for adding navigation to markdown files."""
    
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
        
        # Get navigation config
        self.link_style = config.get('link_style', 'text')
        self.position = config.get('position', 'bottom')
        self.add_top_link = config.get('add_top_link', True)
        self.templates = config.get('templates', {
            'text': {
                'prev': '← Previous: [{title}]({link})',
                'next': 'Next: [{title}]({link}) →',
                'top': '[↑ Back to Top](#table-of-contents)'
            },
            'arrow': {
                'prev': '←',
                'next': '→',
                'top': '↑'
            }
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
        """Process a markdown file by adding navigation.
        
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
            
            # Add navigation
            nav_content = []
            
            # Add top link if enabled
            if self.add_top_link:
                nav_content.append(self.templates[self.link_style]['top'])
            
            # Add previous/next links
            if context.get('prev_file'):
                prev_title = Path(context['prev_file']).stem
                prev_link = f"#{prev_title.lower().replace(' ', '-')}"
                nav_content.append(self.templates[self.link_style]['prev'].format(
                    title=prev_title,
                    link=prev_link
                ))
                
            if context.get('next_file'):
                next_title = Path(context['next_file']).stem
                next_link = f"#{next_title.lower().replace(' ', '-')}"
                nav_content.append(self.templates[self.link_style]['next'].format(
                    title=next_title,
                    link=next_link
                ))
            
            # Add navigation to content
            nav_block = ' | '.join(nav_content)
            if self.position == 'top':
                processed_content = f"{nav_block}\n\n{content}"
            else:
                processed_content = f"{content}\n\n{nav_block}"
            
            # Create output directory structure
            output_path = Path(output_dir) / file_path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write processed content
            output_path.write_text(processed_content, encoding='utf-8')
            
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