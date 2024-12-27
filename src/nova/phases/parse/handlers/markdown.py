"""Handler for parsing markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import asyncio
import os
import shutil

from rich.console import Console

from ....core.base_handler import BaseHandler
from ....core.utils.metrics import MetricsTracker
from ....core.utils.timing import TimingManager
from ....core.models.result import ProcessingResult
from ....core.pipeline.pipeline_state import PipelineState


class MarkdownHandler(BaseHandler):
    """Handler for parsing markdown files."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None,
        pipeline_state: Optional[PipelineState] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional rich console instance
            pipeline_state: Optional pipeline state instance
        """
        super().__init__(config, timing, metrics, console)
        self.pipeline_state = pipeline_state
        
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
            ProcessingResult instance
        """
        context = context or {}
        output_dir = Path(context.get('output_dir', 'output'))
        output_path = output_dir / file_path.name
        
        # Check cache if pipeline state is available
        if self.pipeline_state:
            cached_output = self.pipeline_state.get_cached_output(file_path)
            if cached_output and cached_output.exists():
                self.console.print(f"[cyan]Cache hit for {file_path}[/]")
                # Copy cached output to output directory
                output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cached_output, output_path)
                return ProcessingResult(
                    success=True,
                    output_files=[output_path],
                    metadata={'cached': True}
                )
                
        # Process the file
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Find dependencies (e.g., linked files, images)
            dependencies = await self._find_dependencies(file_path)
            
            # Process markdown
            with self.timing.timer('markdown_processing'):
                # For now, just copy the file
                # TODO: Implement actual markdown processing
                shutil.copy2(file_path, output_path)
                
            # Update cache if pipeline state is available
            if self.pipeline_state:
                self.pipeline_state.update_cache(
                    file_path,
                    output_path,
                    dependencies=dependencies,
                    metadata={'handler': 'markdown'}
                )
                
            return ProcessingResult(
                success=True,
                output_files=[output_path],
                metadata={'cached': False}
            )
            
        except Exception as e:
            self.console.print(f"[red]Error processing {file_path}: {e}[/]")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
            
    async def _find_dependencies(self, file_path: Path) -> Set[Path]:
        """Find dependencies for a markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Set of dependency file paths
        """
        dependencies = set()
        
        try:
            content = file_path.read_text()
            
            # Find image references
            # TODO: Implement proper markdown parsing
            for line in content.split('\n'):
                if '![' in line and '](' in line:
                    start = line.find('](') + 2
                    end = line.find(')', start)
                    if start > 1 and end > start:
                        image_path = line[start:end]
                        if not image_path.startswith(('http://', 'https://')):
                            # Resolve relative path
                            full_path = (file_path.parent / image_path).resolve()
                            if full_path.exists():
                                dependencies.add(full_path)
                                
            # Find linked markdown files
            for line in content.split('\n'):
                if '[' in line and '](' in line:
                    start = line.find('](') + 2
                    end = line.find(')', start)
                    if start > 1 and end > start:
                        link_path = line[start:end]
                        if not link_path.startswith(('http://', 'https://')):
                            # Resolve relative path
                            full_path = (file_path.parent / link_path).resolve()
                            if full_path.exists() and full_path.suffix.lower() == '.md':
                                dependencies.add(full_path)
                                
        except Exception as e:
            self.console.print(f"[yellow]Warning: Error finding dependencies for {file_path}: {e}[/]")
            
        return dependencies 