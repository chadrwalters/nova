"""Pipeline manager."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from nova.core.pipeline.errors import PipelineError, ValidationError
from nova.core.config.base import PipelineConfig
from nova.core.pipeline.pipeline_phase import PipelinePhase
from nova.core.pipeline.pipeline_state import PipelineState
from nova.core.console.pipeline_reporter import PipelineReporter
from nova.core.console.logger import ConsoleLogger
from nova.core.console.color_scheme import ColorScheme
from nova.core.utils.metrics import TimingManager
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.cache import CacheManager


class PipelineManager:
    """Pipeline manager."""

    def __init__(self, config: PipelineConfig):
        """Initialize pipeline manager.
        
        Args:
            config: Pipeline configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.state = PipelineState()
        self.reporter = PipelineReporter()
        self.console = ConsoleLogger()
        self.colors = ColorScheme()
        self.timing = TimingManager()
        self.metrics = MetricsTracker()
        self.cache = None

        # Initialize cache if enabled
        if self.config.cache and self.config.cache.enabled:
            self.cache = CacheManager(
                directory=Path(self.config.cache.directory),
                max_size_mb=self.config.cache.max_size_mb,
                max_age_days=self.config.cache.max_age_days,
                cleanup_on_start=self.config.cache.cleanup_on_start,
                cleanup_on_error=self.config.cache.cleanup_on_error
            )

        # Initialize phases
        self.phases = {}
        for name, phase_config in self.config.phases.items():
            self.phases[name] = PipelinePhase(name, phase_config, self.cache)

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate pipeline configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.phases:
            raise ValidationError("No phases configured")

        # Validate phase dependencies
        self._validate_phase_dependencies()

    def _validate_phase_dependencies(self):
        """Validate phase dependencies.
        
        Raises:
            ValidationError: If dependencies are invalid
        """
        visited = set()
        visiting = set()

        def visit(phase_name: str):
            """Visit phase in dependency graph.
            
            Args:
                phase_name: Name of phase to visit
                
            Raises:
                ValidationError: If dependencies are invalid
            """
            if phase_name in visiting:
                raise ValidationError(f"Circular dependency detected: {phase_name}")
            if phase_name in visited:
                return

            visiting.add(phase_name)
            phase = self.phases.get(phase_name)
            if not phase:
                raise ValidationError(f"Unknown phase: {phase_name}")

            for dep in phase.dependencies:
                visit(dep)

            visiting.remove(phase_name)
            visited.add(phase_name)

        for phase in self.phases:
            visit(phase)

    async def run(self):
        """Run pipeline.
        
        Raises:
            PipelineError: If pipeline execution fails
        """
        try:
            # Initialize cache if enabled
            if self.cache:
                await self.cache.initialize()

            # Run phases
            for phase_name, phase in self.phases.items():
                self.logger.info(f"Running phase: {phase_name}")
                await phase.run()

            self.logger.info("Pipeline completed successfully")

        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            if self.cache and self.cache.cleanup_on_error:
                await self.cache.cleanup()
            raise PipelineError(str(e))

    async def cleanup(self):
        """Clean up pipeline resources."""
        if self.cache:
            await self.cache.cleanup()

        for phase in self.phases.values():
            await phase.cleanup() 