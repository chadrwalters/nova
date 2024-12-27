"""Pipeline state management."""
from typing import Dict, Any, Optional
from pathlib import Path
from nova.core.pipeline.errors import ValidationError, ProcessingError
from nova.core.pipeline.pipeline_config import PipelineConfig
from nova.core.pipeline.pipeline_phase import PipelinePhase
from nova.core.console.pipeline_reporter import PipelineReporter


class PipelineState:
    """Pipeline state manager."""

    def __init__(self, config: PipelineConfig):
        """Initialize pipeline state.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.current_phase: Optional[PipelinePhase] = None
        self.phase_states: Dict[str, Dict[str, Any]] = {}
        self.reporter = PipelineReporter()

    def start_phase(self, phase: PipelinePhase) -> None:
        """Start a phase.
        
        Args:
            phase: The phase to start
        """
        self.current_phase = phase
        self.phase_states[phase.name] = {
            "status": "running",
            "retry_count": 0,
            "error": None
        }
        self.reporter.start_phase(phase.name, 0)

    def complete_phase(self, phase: PipelinePhase) -> None:
        """Complete a phase.
        
        Args:
            phase: The phase to complete
        """
        self.current_phase = None
        self.phase_states[phase.name]["status"] = "completed"
        self.reporter.end_phase(phase.name)

    def handle_phase_error(self, phase: PipelinePhase, error: Exception) -> None:
        """Handle a phase error.
        
        Args:
            phase: The phase that errored
            error: The error that occurred
        """
        phase_state = self.phase_states[phase.name]
        phase_state["error"] = error

        # Check if retries are enabled and available
        max_retries = phase.error_handling.get("max_retries", 0)
        phase_state["retry_count"] = phase_state.get("retry_count", 0) + 1

        if phase_state["retry_count"] < max_retries:
            phase_state["status"] = "retrying"
        else:
            phase_state["status"] = "error" 