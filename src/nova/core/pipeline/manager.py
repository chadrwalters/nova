"""Pipeline manager."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from nova.core.pipeline.errors import PipelineError, ValidationError
from nova.core.pipeline.pipeline_config import PipelineConfig
from nova.core.pipeline.pipeline_phase import PipelinePhase
from nova.core.pipeline.pipeline_state import PipelineState
from nova.core.console.pipeline_reporter import PipelineReporter
from nova.core.console.logger import ConsoleLogger
from nova.core.console.color_scheme import ColorScheme
from nova.core.utils.timing import TimingManager
from nova.core.utils.metrics import MetricsTracker


class PipelineManager:
    """Manages pipeline execution."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize pipeline manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.phases: Dict[str, PipelinePhase] = {}
        self.cache_config = config.cache or {}
        
        # Initialize components
        self.logger = ConsoleLogger()
        self.color_scheme = ColorScheme()
        self.timing = TimingManager()
        self.metrics = MetricsTracker()
        
        # Create reporter with all components
        self.reporter = PipelineReporter(
            logger=self.logger,
            color_scheme=self.color_scheme,
            timing=self.timing,
            metrics=self.metrics
        )
        
        # Initialize phases
        self._initialize_phases()
        
    def _initialize_phases(self) -> None:
        """Initialize pipeline phases."""
        # Store phases and set reporter
        self.phases = self.config.phases
        for phase in self.phases.values():
            phase.reporter = self.reporter
            
            # Set initial cache config
            phase_config = phase.get_cache_config()
            if phase_config:
                # Merge global config with phase-specific config
                phase.set_cache_config({**self.cache_config, **phase_config})
        
    async def _cleanup_phase_cache(self, phase_name: str) -> None:
        """Clean up phase cache.
        
        Args:
            phase_name: Name of the phase
        """
        if not self.cache_config.get('enabled', False):
            return
            
        try:
            phase = self.phases[phase_name]
            cache_dir = phase.get_cache_dir()
            
            if cache_dir and cache_dir.exists():
                self.reporter.logger.info(
                    f"Cleaning up cache for phase {phase_name} in {cache_dir}"
                )
                
                # Get cache stats before cleanup
                cache_size = sum(f.stat().st_size for f in cache_dir.glob('**/*') if f.is_file())
                cache_files = len(list(cache_dir.glob('**/*')))
                
                # Clean up cache
                await phase.cleanup_cache()
                
                self.reporter.logger.info(
                    f"Cleaned up {cache_files} files ({cache_size} bytes) from cache"
                )
                
        except Exception as e:
            self.reporter.logger.warning(
                f"Error cleaning up cache for phase {phase_name}: {e}"
            )
        
    async def process(self, input_files: List[str]) -> Dict[str, Any]:
        """Process input files through the pipeline.
        
        Args:
            input_files: List of input files to process
            
        Returns:
            Processing results
            
        Raises:
            PipelineError: If pipeline execution fails
        """
        try:
            # Start pipeline
            self.reporter.start_pipeline(len(self.phases))
            
            results = {}
            
            # Process each phase
            for phase_name, phase in self.phases.items():
                try:
                    # Start phase
                    self.reporter.start_phase(phase_name, len(input_files))
                    
                    # Process files
                    phase_results = await phase.process(input_files)
                    results[phase_name] = phase_results
                    
                    # Complete phase
                    self.reporter.end_phase(phase_name)
                    
                    # Clean up phase cache if enabled
                    await self._cleanup_phase_cache(phase_name)
                    
                except Exception as e:
                    self.reporter.logger.error(f"Error in phase {phase_name}: {e}")
                    raise
                    
            # End pipeline
            self.reporter.end_pipeline()
            
            return results
            
        except Exception as e:
            raise PipelineError(f"Pipeline execution failed: {e}")
        
    async def cleanup(self) -> None:
        """Clean up pipeline resources."""
        # Clean up phases
        for phase in self.phases.values():
            await phase.cleanup()
            
        # Final cache cleanup if enabled
        if self.cache_config.get('enabled', False):
            for phase_name in self.phases:
                await self._cleanup_phase_cache(phase_name)
                
    def get_reporter(self) -> PipelineReporter:
        """Get pipeline reporter.
        
        Returns:
            Pipeline reporter instance
        """
        return self.reporter
        
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration.
        
        Returns:
            Cache configuration dictionary
        """
        return self.cache_config.copy()
        
    def set_cache_config(self, config: Dict[str, Any]) -> None:
        """Update cache configuration.
        
        Args:
            config: New cache configuration
        """
        self.cache_config.update(config)
        
        # Update phase-specific cache configs
        for phase in self.phases.values():
            phase_config = phase.get_cache_config()
            if phase_config:
                # Merge global config with phase-specific config
                merged_config = {**self.cache_config, **phase_config}
                # Force disabled state from global config
                if not self.cache_config.get('enabled', True):
                    merged_config['enabled'] = False
                phase.set_cache_config(merged_config)