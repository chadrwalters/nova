"""Base handler for all phase handlers."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger


class BaseHandler:
    """Base handler for all phase handlers."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize base handler.
        
        Args:
            name: Handler name
            options: Handler options
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
        """
        self.name = name
        self.options = options
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.monitoring = monitoring or MonitoringManager()
        self.console = console or ConsoleLogger()
        self.logger = logging.getLogger(__name__)

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if handler can process file, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement can_handle()")

    async def process(self, file_path: Path, context: Dict[str, Any]) -> HandlerResult:
        """Process file.
        
        Args:
            file_path: Path to file
            context: Processing context
            
        Returns:
            Handler result
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process()")

    def validate_output(self, result: HandlerResult) -> bool:
        """Validate handler result.
        
        Args:
            result: Handler result
            
        Returns:
            True if result is valid, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement validate_output()")

    async def cleanup(self):
        """Clean up handler resources.
        
        This method should be implemented by subclasses.
        """
        pass

    def get_name(self) -> str:
        """Get handler name.
        
        Returns:
            Handler name
        """
        return self.name

    def get_options(self) -> Dict[str, Any]:
        """Get handler options.
        
        Returns:
            Handler options
        """
        return self.options

    def get_timing(self) -> TimingManager:
        """Get timing manager.
        
        Returns:
            Timing manager
        """
        return self.timing

    def get_metrics(self) -> MetricsTracker:
        """Get metrics tracker.
        
        Returns:
            Metrics tracker
        """
        return self.metrics

    def get_monitoring(self) -> MonitoringManager:
        """Get monitoring manager.
        
        Returns:
            Monitoring manager
        """
        return self.monitoring

    def get_console(self) -> ConsoleLogger:
        """Get console logger.
        
        Returns:
            Console logger
        """
        return self.console 