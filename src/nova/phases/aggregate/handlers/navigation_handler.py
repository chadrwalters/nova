"""Handler for adding navigation to markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import os
from rich.console import Console

from nova.core.base_handler import BaseHandler
from nova.core.models.result import ProcessingResult


class NavigationHandler(BaseHandler):
    """Handler for adding navigation to markdown files."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        console: Optional[Console] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Configuration dictionary
            console: Optional console instance
        """
        super().__init__(config=config, console=console)
        
        # Get required configuration
        if not config:
            raise ValueError("Configuration must be provided")
            
        # Get pipeline and processor configs
        self.pipeline_config = config.get('pipeline_config', {})
        self.processor_config = config.get('processor_config', {})
        
        # Get required paths
        self.input_dir = str(Path(config.get('input_dir', '')))
        self.output_dir = str(Path(config.get('output_dir', '')))
        self.base_dir = str(Path(config.get('base_dir', '')))
        
        if not self.input_dir or not self.output_dir:
            raise ValueError("input_dir and output_dir must be specified in configuration")
        
        # Get navigation configuration
        self.nav_config = config.get('navigation', {})
        self.link_style = self.nav_config.get('link_style', 'text')
        self.add_top_link = self.nav_config.get('add_top_link', True)
        
        # Configure navigation templates
        self.templates = {
            'text': {
                'prev': "← Previous: [{title}]({link})",
                'next': "Next: [{title}]({link}) →",
                'top': "[↑ Back to Top](#table-of-contents)"
            },
            'arrow': {
                'prev': "←",
                'next': "→",
                'top': "↑"
            }
        }
    
    async def initialize(self) -> None:
        """Initialize the handler."""
        await super().initialize()
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processed content and metadata
        """
        try:
            # Use configured output directory
            output_dir = Path(self.output_dir)
            
            async with self.monitoring.async_monitor_operation("read_file"):
                # Read input file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Record file size metric
                self.monitoring.set_gauge("file_size", file_path.stat().st_size)
            
            async with self.monitoring.async_monitor_operation("process_content"):
                # Get navigation context
                prev_link = context.get('prev_link', {}) if context else {}
                next_link = context.get('next_link', {}) if context else {}
                
                # Add navigation
                nav_content = []
                
                # Add previous link if available
                if prev_link:
                    template = self.templates[self.link_style]['prev']
                    nav_content.append(template.format(
                        title=prev_link.get('title', ''),
                        link=prev_link.get('link', '')
                    ))
                
                # Add next link if available
                if next_link:
                    template = self.templates[self.link_style]['next']
                    nav_content.append(template.format(
                        title=next_link.get('title', ''),
                        link=next_link.get('link', '')
                    ))
                
                # Add top link if enabled
                if self.add_top_link:
                    nav_content.append(self.templates[self.link_style]['top'])
                
                # Combine navigation with content
                processed_content = content
                if nav_content:
                    nav_section = "\n\n---\n\n" + " | ".join(nav_content)
                    processed_content += nav_section
                
                # Record content metrics
                self.monitoring.set_gauge("content_lines", len(content.splitlines()))
                if nav_content:
                    self.monitoring.increment_counter("navigation_links_added")
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=processed_content,
                metadata={
                    'input_file': str(file_path),
                    'output_dir': str(output_dir),
                    'file_size': file_path.stat().st_size,
                    'line_count': len(content.splitlines()),
                    'has_navigation': bool(nav_content)
                }
            )
            result.add_processed_file(file_path)
            
            # Record success metrics
            self.monitoring.increment_counter("files_processed")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.monitoring.record_error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
    
    async def _post_process(self, result: ProcessingResult) -> None:
        """Run post-processing hooks.
        
        Args:
            result: Processing result
        """
        try:
            async with self.monitoring.async_monitor_operation("post_process"):
                for hook in self._post_process_hooks:
                    await hook(result)
        except Exception as e:
            self.monitoring.record_error(f"Error in post-processing: {str(e)}")
    
    async def _on_error(self, error: Exception, result: ProcessingResult) -> None:
        """Run error hooks.
        
        Args:
            error: Exception that occurred
            result: Processing result
        """
        try:
            async with self.monitoring.async_monitor_operation("error_hooks"):
                for hook in self._error_hooks:
                    await hook(error, result)
        except Exception as e:
            self.monitoring.record_error(f"Error in error hooks: {str(e)}")
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def _cleanup_impl(self) -> None:
        """Clean up resources."""
        try:
            async with self.monitoring.async_monitor_operation("cleanup"):
                # Clean up any processed files that had errors
                for file_path in self.processed_files:
                    if file_path.exists() and not self.validate_output(file_path):
                        file_path.unlink()
        except Exception as e:
            self.monitoring.record_error(f"Error during cleanup: {str(e)}")
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        try:
            async with self.monitoring.async_monitor_operation("rollback"):
                # Clean up any created files
                for file_path in result.processed_files:
                    try:
                        if file_path.exists():
                            file_path.unlink()
                    except Exception as e:
                        error_msg = f"Error cleaning up file {file_path}: {str(e)}"
                        self.monitoring.record_error(error_msg)
        except Exception as e:
            self.monitoring.record_error(f"Error during rollback: {str(e)}") 