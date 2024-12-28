"""Metadata handler for splitting markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.phases.core.base_handler import BaseHandler


class MetadataHandler(BaseHandler):
    """Metadata handler for splitting markdown files."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize metadata handler.
        
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
            
            # Extract metadata
            metadata = self._extract_metadata(content)
            
            # Write metadata to file
            output_file = result.output_dir / file_path.stem / 'metadata.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert lists to strings in metadata
            processed_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    processed_metadata[key] = '\n'.join(value)
                else:
                    processed_metadata[key] = value
            
            # Write metadata
            output_file.write_text(json.dumps(processed_metadata, indent=2))
            
            # Update result
            result.success = True
            result.output_files.append(output_file)
            result.content = content
            result.metadata = metadata
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content.
        
        Args:
            content: Content to extract metadata from
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'sections': [],
            'attachments': [],
            'references': []
        }

        # Process content line by line
        for line in content.split('\n'):
            # Check for section markers
            if line.startswith('--=='):
                section = line.strip('-=').strip()
                metadata['sections'].append(section)

            # Check for attachment blocks
            elif line.startswith('--==ATTACHMENT_BLOCK:'):
                attachment = line.split(':')[1].strip('-=').strip()
                metadata['attachments'].append(attachment)

            # Check for references
            elif line.startswith('[') and '](' in line:
                reference = line[line.find('(')+1:line.find(')')]
                metadata['references'].append(reference)

        return metadata

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
            'attachments' in result.metadata and
            'references' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 