"""Pipeline manager for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ..config import PipelineConfig, PathConfig, ProcessorConfig
from ..utils.logging import get_logger
from ..errors import PipelineError
from .phase import PhaseType, PipelinePhase, PIPELINE_PHASES

class PipelineManager:
    """Manages the document processing pipeline."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the pipeline manager.
        
        Args:
            config: Optional pipeline configuration
        """
        self.logger = get_logger(__name__)
        
        # Create default config if none provided
        if not config:
            config = PipelineConfig(
                paths=PathConfig(base_dir=Path.cwd()),
                processors={}
            )
        
        self.config = config
        self.phases: Dict[PhaseType, PipelinePhase] = {}
        self._initialize_phases()
    
    def _initialize_phases(self) -> None:
        """Initialize pipeline phases."""
        for phase_def in PIPELINE_PHASES:
            # Get or create processor config
            processor_config = self.config.processors.get(
                phase_def.type.name,
                ProcessorConfig()
            )
            
            # Create phase
            self.phases[phase_def.type] = PipelinePhase(
                definition=phase_def,
                processor_config=processor_config,
                pipeline_config=self.config
            )
    
    def _get_phase_range(
        self,
        start_phase: Optional[PhaseType] = None,
        end_phase: Optional[PhaseType] = None
    ) -> List[PhaseType]:
        """Get list of phases to process.
        
        Args:
            start_phase: Optional phase to start from
            end_phase: Optional phase to end at
            
        Returns:
            List of phases to process
        """
        phases = list(PhaseType)
        
        if start_phase:
            start_idx = phases.index(start_phase)
            phases = phases[start_idx:]
        
        if end_phase:
            end_idx = phases.index(end_phase) + 1
            phases = phases[:end_idx]
        
        return phases
    
    def process_phase(
        self,
        phase_type: PhaseType,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """Process a single phase.
        
        Args:
            phase_type: Type of phase to process
            input_path: Path to input file or directory
            output_path: Path to output file or directory
            
        Returns:
            Dict containing processing results
            
        Raises:
            PipelineError: If processing fails
        """
        phase = self.phases.get(phase_type)
        if not phase:
            raise PipelineError(f"Unknown phase: {phase_type}")
        
        try:
            self.logger.info(f"Processing phase: {phase.name}")
            result = phase.process(input_path, output_path)
            self.logger.info(f"Completed phase: {phase.name}")
            return result
            
        except Exception as e:
            error = f"Error in phase {phase.name}: {str(e)}"
            self.logger.error(error)
            raise PipelineError(error) from e
    
    def run_pipeline(
        self,
        input_path: str,
        output_path: str,
        start_phase: Optional[PhaseType] = None,
        end_phase: Optional[PhaseType] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Run the complete pipeline or a subset of phases.
        
        Args:
            input_path: Path to input file or directory
            output_path: Path to output file or directory
            start_phase: Optional phase to start from
            end_phase: Optional phase to end at
            options: Optional processing options
            
        Returns:
            bool: True if pipeline completed successfully
        """
        try:
            # Get phases to process
            phases = self._get_phase_range(start_phase, end_phase)
            if not phases:
                raise PipelineError("No phases to process")
            
            # Process each phase
            current_input = input_path
            for i, phase_type in enumerate(phases):
                # For the last phase, use the final output path
                if i == len(phases) - 1:
                    current_output = output_path
                else:
                    # Get phase directory from environment
                    phase_env_var = f"NOVA_PHASE_{phase_type.name}"
                    phase_dir = self.config.paths.get_phase_dir(phase_type)
                    if not phase_dir:
                        raise PipelineError(f"Missing phase directory for {phase_type.name}")
                    current_output = str(phase_dir)
                
                # Process phase
                result = self.process_phase(phase_type, current_input, current_output)
                
                # Use output as input for next phase
                current_input = current_output
            
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current pipeline state.
        
        Returns:
            Dict containing pipeline state
        """
        return {
            phase_type.name: phase.get_state()
            for phase_type, phase in self.phases.items()
        }
    
    def reset_state(self) -> None:
        """Reset pipeline state."""
        self._initialize_phases() 