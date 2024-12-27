"""Pipeline manager."""
from typing import Dict, Any, List, Optional
from pathlib import Path
from nova.core.pipeline.errors import ValidationError, ProcessingError
from nova.core.pipeline.pipeline_config import PipelineConfig
from nova.core.pipeline.pipeline_phase import PipelinePhase
from nova.core.pipeline.pipeline_state import PipelineState


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
        self.state = PipelineState(config)
        self.phases = config.phases

    def execute_phase(self, phase_name: str) -> None:
        """Execute a pipeline phase.
        
        Args:
            phase_name: Name of the phase to execute
            
        Raises:
            KeyError: If phase does not exist
            ProcessingError: If phase execution fails
        """
        phase = self.phases[phase_name]
        self.state.start_phase(phase)

        try:
            # Execute phase
            processor = phase.processor()
            processor.process()
            self.state.complete_phase(phase)
        except Exception as e:
            self.handle_phase_error(phase_name, e)
            raise

    def handle_phase_error(self, phase_name: str, error: Exception) -> None:
        """Handle a phase error.
        
        Args:
            phase_name: Name of the phase that errored
            error: The error that occurred
        """
        phase = self.phases[phase_name]
        self.state.handle_phase_error(phase, error)

    def get_phase_dependencies(self, phase_name: str) -> List[str]:
        """Get phase dependencies.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            List of phase names this phase depends on
            
        Raises:
            KeyError: If phase does not exist
        """
        return self.config.get_phase_dependencies(phase_name)

    def get_phase_status(self, phase_name: str) -> str:
        """Get phase status.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Phase status
            
        Raises:
            KeyError: If phase does not exist
        """
        return self.state.phase_states[phase_name]["status"]

    def get_phase_progress(self, phase_name: str) -> int:
        """Get phase progress.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Progress percentage (0-100)
            
        Raises:
            KeyError: If phase does not exist
        """
        return self.state.reporter.get_phase_progress(phase_name) 