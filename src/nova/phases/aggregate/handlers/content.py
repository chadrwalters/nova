"""Content handler for aggregating markdown files."""

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
    """Content handler for aggregating markdown files."""

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

            # Aggregate content
            if isinstance(content, dict):
                # If content is already a dictionary of sections, join them
                aggregated_content = '\n\n'.join(content.values())
            else:
                # Otherwise aggregate normally
                aggregated_content = self._aggregate_content(content)

            # Write aggregated content
            output_dir = Path(context['output_dir'])
            output_file = output_dir / f"{file_path.stem}_aggregated.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(aggregated_content)

            return HandlerResult(
                success=True,
                content=aggregated_content,
                metadata={
                    'output_file': str(output_file)
                }
            )

        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)

    def _aggregate_content(self, content: str) -> str:
        """Aggregate content.
        
        Args:
            content: Content to aggregate
            
        Returns:
            Aggregated content
        """
        sections = []
        current_section = []
        in_aggregate_block = False

        # Process content line by line
        for line in content.split('\n'):
            # Check for aggregate block markers
            if line.startswith('--==AGGREGATE_BLOCK:'):
                in_aggregate_block = True
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
                continue
            elif line.startswith('--==AGGREGATE_BLOCK_END==--'):
                in_aggregate_block = False
                current_section.append(line)
                sections.append('\n'.join(current_section))
                current_section = []
                continue

            # Add line to current section
            if in_aggregate_block:
                current_section.append(line)
            else:
                sections.append(line)

        # Add any remaining content
        if current_section:
            sections.append('\n'.join(current_section))

        # Join sections
        return '\n'.join(sections)

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
            'output_file' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 