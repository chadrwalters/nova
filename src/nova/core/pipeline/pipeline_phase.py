"""Pipeline phase."""

import logging
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional

from nova.core.errors import ValidationError
from nova.core.utils.cache import CacheManager
from nova.core.config.base import ProcessorConfig
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.core.pipeline.pipeline_state import PipelineState


class PipelinePhase:
    """Pipeline phase."""

    def __init__(self, name: str, config: Dict[str, Any], cache: Optional[CacheManager] = None):
        """Initialize pipeline phase.
        
        Args:
            name: Phase name
            config: Phase configuration
            cache: Optional cache manager
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.name = name
        self.config = config
        self.cache = cache
        self.logger = logging.getLogger(__name__)

        # Initialize required attributes
        self.description = config.get('description', '')
        self.processor_name = config.get('processor')
        self.input_dir = Path(config['input_dir']) if 'input_dir' in config else None
        self.output_dir = Path(config['output_dir']) if 'output_dir' in config else None
        self.components = config.get('components', {})
        self.dependencies = config.get('dependencies', [])

        # Initialize optional attributes
        self.timing = TimingManager()
        self.metrics = MetricsTracker()
        self.monitoring = MonitoringManager()
        self.console = ConsoleLogger()
        self.pipeline_state = PipelineState()

        # Initialize processor class
        self.processor = None
        self._initialize_processor()

        # Validate configuration
        self._validate_config()

    def _initialize_processor(self):
        """Initialize processor class.
        
        Raises:
            ValidationError: If processor initialization fails
        """
        try:
            # Map phase names to module paths
            module_paths = {
                'MARKDOWN_PARSE': 'nova.phases.parse.processor',
                'MARKDOWN_CONSOLIDATE': 'nova.phases.consolidate.processor',
                'MARKDOWN_AGGREGATE': 'nova.phases.aggregate.processor',
                'MARKDOWN_SPLIT': 'nova.phases.split.processor'
            }

            # Get module path for this phase
            module_path = module_paths.get(self.name)
            if not module_path:
                # Fallback to default path construction
                phase_type = self.name.split('_')[1].lower()  # Use second part (MARKDOWN_PARSE -> parse)
                module_path = f"nova.phases.{phase_type}.processor"

            # Import processor class
            module = importlib.import_module(module_path)
            processor_class = getattr(module, self.processor_name)

            # Create processor config
            processor_config = ProcessorConfig(
                name=self.name,
                description=self.description,
                processor=self.processor_name,
                input_dir=str(self.input_dir) if self.input_dir else None,
                output_dir=str(self.output_dir) if self.output_dir else None,
                components=self.components,
                cache=self.config.get('cache', {})
            )

            # Initialize processor
            self.processor = processor_class(
                config=processor_config,
                timing=self.timing,
                metrics=self.metrics,
                console=self.console,
                pipeline_state=self.pipeline_state,
                monitoring=self.monitoring
            )

        except Exception as e:
            raise ValidationError(f"Failed to initialize processor: {str(e)}")

    def _validate_config(self):
        """Validate phase configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate required attributes
        if not self.processor_name:
            raise ValidationError(f"Missing processor for phase {self.name}")
        if not self.input_dir:
            raise ValidationError(f"Missing input directory for phase {self.name}")
        if not self.output_dir:
            raise ValidationError(f"Missing output directory for phase {self.name}")

        # Validate dependencies
        for dep in self.dependencies:
            if not isinstance(dep, str):
                raise ValidationError(f"Invalid dependency type for phase {self.name}: {type(dep)}")

    async def run(self):
        """Run pipeline phase.
        
        Raises:
            ValidationError: If phase execution fails
        """
        try:
            self.logger.info(f"Running phase {self.name}")

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Run processor
            await self.processor.process()

            self.logger.info(f"Phase {self.name} completed successfully")

        except Exception as e:
            self.logger.error(f"Phase {self.name} failed: {str(e)}")
            raise ValidationError(f"Phase {self.name} failed: {str(e)}")

    async def cleanup(self):
        """Clean up phase resources."""
        try:
            # Clean up output directory
            if self.output_dir and self.output_dir.exists():
                for file in self.output_dir.glob('**/*'):
                    if file.is_file():
                        file.unlink()

            # Clean up cache if enabled
            if self.cache and self.config.get('cache', {}).get('cleanup_on_complete', True):
                await self.cache.cleanup()

            # Clean up processor
            if self.processor:
                await self.processor.cleanup()

        except Exception as e:
            self.logger.error(f"Error cleaning up phase {self.name}: {str(e)}")

    def get_input_dir(self) -> Path:
        """Get phase input directory.
        
        Returns:
            Input directory path
        """
        return self.input_dir

    def get_output_dir(self) -> Path:
        """Get phase output directory.
        
        Returns:
            Output directory path
        """
        return self.output_dir

    def get_dependencies(self) -> List[str]:
        """Get phase dependencies.
        
        Returns:
            List of dependency phase names
        """
        return self.dependencies

    def get_cache_config(self) -> Dict[str, Any]:
        """Get phase cache configuration.
        
        Returns:
            Cache configuration dictionary
        """
        return self.config.get('cache', {})

    def set_cache_config(self, config: Dict[str, Any]):
        """Set phase cache configuration.
        
        Args:
            config: Cache configuration dictionary
        """
        self.config['cache'] = config 