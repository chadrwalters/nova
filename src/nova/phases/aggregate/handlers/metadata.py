"""Metadata handler for aggregating markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.phases.core.base_handler import BaseHandler


class MetadataHandler(BaseHandler):
    """Metadata handler for aggregating markdown files."""

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
        """Process markdown file.
        
        Args:
            file_path: Path to file
            context: Processing context
            
        Returns:
            Handler result
            
        Raises:
            ValidationError: If processing fails
        """
        try:
            self.logger.info(f"Processing file: {file_path}")

            # Read file content
            content = file_path.read_text()

            # Extract metadata
            metadata = self._extract_metadata(content)

            # Write metadata to file
            output_dir = Path(context['output_dir'])
            metadata_file = output_dir / f"{file_path.stem}_metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            metadata_file.write_text(str(metadata))

            return HandlerResult(
                success=True,
                content=content,
                metadata=metadata
            )

        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content.
        
        Args:
            content: Content to extract metadata from
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'aggregate_blocks': [],
            'references': [],
            'statistics': {
                'total_blocks': 0,
                'total_references': 0,
                'total_lines': 0
            }
        }

        # Process content line by line
        for line in content.split('\n'):
            metadata['statistics']['total_lines'] += 1

            # Check for aggregate block markers
            if line.startswith('--==AGGREGATE_BLOCK:'):
                block_name = line.split(':')[1].strip('-=').strip()
                metadata['aggregate_blocks'].append(block_name)
                metadata['statistics']['total_blocks'] += 1

            # Check for references
            elif line.startswith('[') and '](' in line:
                reference = line[line.find('(')+1:line.find(')')]
                metadata['references'].append(reference)
                metadata['statistics']['total_references'] += 1

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
            'aggregate_blocks' in result.metadata and
            'references' in result.metadata and
            'statistics' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 