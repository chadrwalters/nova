"""Content handler for splitting markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.phases.core.base_handler import BaseHandler


class ContentHandler(BaseHandler):
    """Content handler for splitting markdown files."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize content handler.
        
        Args:
            name: Handler name
            options: Handler options
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
        """
        super().__init__(
            name=name,
            options=options,
            timing=timing,
            metrics=metrics,
            monitoring=monitoring,
            console=console
        )
        self.logger = logging.getLogger(__name__)

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if handler can process file, False otherwise
        """
        return file_path.suffix.lower() == '.md'

    async def process(self, file_path: Path, context: Dict[str, Any]) -> HandlerResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file
            context: Processing context
            
        Returns:
            HandlerResult containing processed content and metadata
        """
        try:
            # Initialize result
            result = HandlerResult()
            result.input_file = file_path
            result.output_dir = Path(context.get('output_dir', ''))
            
            # Read content
            content = file_path.read_text()
            
            # Split content
            sections = self._split_content(content)
            
            # Write sections to separate files
            output_files = []
            for section_name, section_content in sections.items():
                if isinstance(section_content, list):
                    section_content = '\n'.join(section_content)
                    
                output_file = result.output_dir / file_path.stem / f"{section_name}.md"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(section_content)
                output_files.append(output_file)
            
            # Update result
            result.success = True
            result.output_files.extend(output_files)
            result.content = content
            result.metadata = {
                'sections': sections,
                'section_files': {
                    section: str(output_files[i])
                    for i, section in enumerate(sections.keys())
                }
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)

    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into sections.
        
        Args:
            content: Content to split
            
        Returns:
            Dictionary of section name to content
        """
        sections = {
            'summary': [],
            'notes': [],
            'attachments': []
        }
        current_section = None

        # Process content line by line
        for line in content.split('\n'):
            # Check for section headers
            if line.strip().lower().startswith('# summary') or line.strip().lower().startswith('# executive summary'):
                current_section = 'summary'
                sections[current_section].append(line)
                continue
            elif line.strip().lower().startswith('# notes') or line.strip().lower().startswith('# raw notes'):
                current_section = 'notes'
                sections[current_section].append(line)
                continue
            elif line.strip().lower().startswith('# attachments') or line.strip().lower().startswith('# embedded content'):
                current_section = 'attachments'
                sections[current_section].append(line)
                continue
            
            # Add line to current section if we have one
            if current_section:
                sections[current_section].append(line)
            # If no section yet, add to summary
            else:
                sections['summary'].append(line)

        # Join sections
        return {
            name: '\n'.join(lines).strip()
            for name, lines in sections.items()
        }

    def validate_output(self, result: HandlerResult) -> bool:
        """Validate handler result.
        
        Args:
            result: Handler result
            
        Returns:
            True if result is valid, False otherwise
        """
        return (
            result.success and
            isinstance(result.content, str) and
            isinstance(result.metadata, dict) and
            'sections' in result.metadata and
            'section_files' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 