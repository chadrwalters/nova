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
    
    async def process(self, file_path: Union[str, Path], context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing parsed content and metadata
        """
        try:
            # Convert string path to Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            # Read input file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse sections
            sections = self._parse_sections(content)
            
            # Get output directory from context or config
            output_dir = None
            if context and 'output_dir' in context:
                output_dir = Path(context['output_dir'])
            elif self.config and 'output_dir' in self.config:
                output_dir = Path(self.config['output_dir'])
            
            if not output_dir:
                raise ValueError("No output directory specified")
            
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
                    'output_file': str(output_file)
                }
            )
            result.add_processed_file(file_path)
            result.add_processed_file(output_file)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
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
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def cleanup(self) -> None:
        """Clean up resources.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        pass 