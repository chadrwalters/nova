"""Handler for parsing markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re
import shutil

from .....core.base_handler import BaseHandler
from .....core.models.result import ProcessingResult


class MarkdownHandler(BaseHandler):
    """Handler for parsing markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize section patterns
        self.section_patterns = {
            'summary': r'#\s+Summary|Executive\s+Summary',
            'raw_notes': r'#\s+Notes|Raw\s+Notes',
            'attachments': r'#\s+Attachments|Embedded\s+Content'
        }
        
        # Initialize metrics
        self.monitoring.set_threshold("memory_percent", 85.0)
    
    async def can_handle(self, file_path: Union[str, Path]) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        # Convert string path to Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        return file_path.suffix.lower() == '.md'
    
    async def _process_impl(self, file_path: Union[str, Path], context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing parsed content and metadata
        """
        # Convert string path to Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        try:
            async with self.monitoring.async_monitor_operation("read_file"):
                # Monitor resource usage
                usage = self.monitoring.capture_resource_usage()
                self.monitoring._check_thresholds(usage)
                
                # Read input file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Record file size
                file_size = file_path.stat().st_size
                self.state.add_metric("file_size", file_size)
            
            async with self.monitoring.async_monitor_operation("parse_sections"):
                # Parse sections
                sections = self._parse_sections(content)
                
                # Record section counts
                for section, lines in sections.items():
                    self.state.add_metric(f"{section}_lines", len(lines))
            
            # Get output directory from context or config
            output_dir = None
            if context and 'output_dir' in context:
                output_dir = Path(context['output_dir'])
            elif self.config and 'output_dir' in self.config:
                output_dir = Path(self.config['output_dir'])
            
            if not output_dir:
                error_msg = "No output directory specified"
                self.monitoring.record_error(error_msg)
                return ProcessingResult(success=False, errors=[error_msg])
            
            async with self.monitoring.async_monitor_operation("write_output"):
                try:
                    # Create output directory if it doesn't exist
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file to output directory
                    output_file = output_dir / file_path.name
                    shutil.copy2(file_path, output_file)
                    
                    # Create result
                    result = ProcessingResult(
                        success=True,
                        content=content,
                        metadata={
                            'sections': sections,
                            'output_file': str(output_file),
                            'metrics': self.state.metrics
                        }
                    )
                    result.add_processed_file(file_path)
                    result.add_processed_file(output_file)
                    
                    # Record success metrics
                    self.monitoring.increment_counter("files_processed")
                    
                    return result
                    
                except Exception as e:
                    error_msg = f"Error writing output for {file_path}: {str(e)}"
                    self.monitoring.record_error(error_msg)
                    return ProcessingResult(success=False, errors=[error_msg])
                
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.monitoring.record_error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
    
    def _parse_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse content sections.
        
        Args:
            content: Content to parse
            
        Returns:
            Dictionary of parsed sections
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Split content into lines
        lines = content.split('\n')
        
        # Track current section
        current_section = None
        section_content = []
        
        # Process each line
        for line in lines:
            # Check for section headers
            for section, pattern in self.section_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    # Save previous section content
                    if current_section and section_content:
                        sections[current_section].extend(section_content)
                    
                    # Start new section
                    current_section = section
                    section_content = []
                    break
            
            # Add line to current section
            if current_section:
                section_content.append(line)
        
        # Add final section content
        if current_section and section_content:
            sections[current_section].extend(section_content)
        
        return sections
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        if not result.success or not result.content:
            self.monitoring.record_error("Invalid processing result")
            return False
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self._cleanup_impl()
        except Exception as e:
            self.monitoring.record_error(f"Error during cleanup: {str(e)}")
            raise 