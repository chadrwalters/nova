"""Handler for classifying markdown content."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from ....core.base_handler import BaseHandler
from ....core.models.result import ProcessingResult


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
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing classified content and metadata
        """
        try:
            # Read input file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Classify content sections
            sections = self._classify_sections(content)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=content,
                metadata={'sections': sections}
            )
            result.add_processed_file(file_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            return ProcessingResult(success=False, errors=[error_msg])
    
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