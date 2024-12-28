"""Base class for markdown handlers."""
# Standard library imports
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Third-party imports
from rich.console import Console

# Nova package imports
from nova.core.exceptions import ValidationError
from nova.core.models.result import ProcessingResult
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import MetricsTracker, MonitoringManager, TimingManager
from nova.phases.parse.handlers.base_handler import BaseHandler


class BaseMarkdownHandler(BaseHandler):
    """Base class for markdown handlers."""

    def __init__(self, config: Dict[str, Any], timing: TimingManager,
                 metrics: MetricsTracker, console: Console,
                 pipeline_state: PipelineState,
                 monitoring: Optional[MonitoringManager] = None) -> None:
        """Initialize the handler."""
        super().__init__(config, timing, metrics, console, pipeline_state, monitoring)
        self.section_patterns = {}
        self.optional_sections = set()

    def can_handle(self, file_path: Path) -> bool:
        """Check if the handler can process the file."""
        if not file_path.exists():
            if self.monitoring:
                self.monitoring.record_error(f"File {file_path} does not exist")
            return False
        elif not file_path.is_file():
            if self.monitoring:
                self.monitoring.record_error(f"Path {file_path} is not a file")
            return False
        return file_path.suffix.lower() == '.md'

    def _validate_section_patterns(self) -> None:
        """Validate section patterns configuration."""
        if not self.section_patterns:
            raise ValidationError("No section patterns defined")
        for name, pattern in self.section_patterns.items():
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValidationError(f"Invalid regex pattern for section '{name}': {e}")

    def _parse_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse sections from markdown content.
        
        This method should be implemented by subclasses to provide specific
        section parsing logic.
        """
        raise NotImplementedError("Subclasses must implement _parse_sections")

    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        This method should be implemented by subclasses to provide specific
        processing logic.
        """
        raise NotImplementedError("Subclasses must implement _process_impl") 