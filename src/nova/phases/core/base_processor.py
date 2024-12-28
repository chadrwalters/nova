"""Base processor for pipeline phases."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from nova.core.errors import ValidationError
from nova.core.config.base import ProcessorConfig
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.core.pipeline.pipeline_state import PipelineState


class BaseProcessor:
    """Base processor for pipeline phases."""

    def __init__(
        self,
        config: ProcessorConfig,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None,
        pipeline_state: Optional[PipelineState] = None
    ):
        """Initialize base processor.
        
        Args:
            config: Processor configuration
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
            pipeline_state: Optional pipeline state
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.config = config
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.monitoring = monitoring or MonitoringManager()
        self.console = console or ConsoleLogger()
        self.pipeline_state = pipeline_state or PipelineState()
        self.logger = logging.getLogger(__name__)

        # Extract required paths from config
        self.input_dir = Path(config.input_dir) if config.input_dir else None
        self.output_dir = Path(config.output_dir) if config.output_dir else None
        self.temp_dir = Path(config.temp_dir) if hasattr(config, 'temp_dir') else None

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate processor configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.input_dir:
            raise ValidationError("Missing input directory")
        if not self.output_dir:
            raise ValidationError("Missing output directory")

    async def process(self):
        """Process files.
        
        This method should be implemented by subclasses.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process()")

    async def cleanup(self):
        """Clean up processor resources.
        
        This method should be implemented by subclasses.
        """
        try:
            # Clean up output directory
            if self.output_dir and self.output_dir.exists():
                for file in self.output_dir.glob('**/*'):
                    if file.is_file():
                        file.unlink()

            # Clean up temp directory
            if self.temp_dir and self.temp_dir.exists():
                for file in self.temp_dir.glob('**/*'):
                    if file.is_file():
                        file.unlink()

        except Exception as e:
            self.logger.error(f"Error cleaning up processor: {str(e)}")

    def get_input_dir(self) -> Path:
        """Get processor input directory.
        
        Returns:
            Input directory path
        """
        return self.input_dir

    def get_output_dir(self) -> Path:
        """Get processor output directory.
        
        Returns:
            Output directory path
        """
        return self.output_dir

    def get_temp_dir(self) -> Optional[Path]:
        """Get processor temporary directory.
        
        Returns:
            Temporary directory path if configured, None otherwise
        """
        return self.temp_dir

    def get_config(self) -> ProcessorConfig:
        """Get processor configuration.
        
        Returns:
            Processor configuration
        """
        return self.config

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

    def get_pipeline_state(self) -> PipelineState:
        """Get pipeline state.
        
        Returns:
            Pipeline state
        """
        return self.pipeline_state 