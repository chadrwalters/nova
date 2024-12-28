"""Handler for classifying markdown content."""

# Standard library imports
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Nova package imports
from nova.core.base_handler import BaseHandler
from nova.core.models.result import ProcessingResult
from nova.core.exceptions import ValidationError


class ClassificationHandler(BaseHandler):
    """Handler for classifying markdown content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize classification patterns
        self.patterns = {
            'summary': r'#\s+Summary|Executive\s+Summary',
            'raw_notes': r'#\s+Notes|Raw\s+Notes',
            'attachments': r'#\s+Attachments|Embedded\s+Content'
        }
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Processing context
            
        Returns:
            ProcessingResult containing classified content and metadata
        """
        try:
            # Initialize result
            result = ProcessingResult()
            result.input_file = file_path
            result.output_dir = Path(context.get('output_dir', ''))
            
            # Read content
            content = file_path.read_text()
            
            # Classify sections
            sections = self._classify_sections(content)
            
            # Create output file
            output_file = result.output_dir / file_path.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content)
            
            # Update result
            result.success = True
            result.output_files.append(output_file)
            result.content = content
            result.metadata = {
                'sections': sections,
                'classification': {
                    'has_summary': bool(sections.get('summary')),
                    'has_notes': bool(sections.get('raw_notes')),
                    'has_attachments': bool(sections.get('attachments'))
                }
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)
    
    def _classify_sections(self, content: str) -> Dict[str, List[str]]:
        """Classify content sections.
        
        Args:
            content: Content to classify
            
        Returns:
            Dictionary of classified sections
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
            for section, pattern in self.patterns.items():
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
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        # No changes to roll back for this handler
        pass 