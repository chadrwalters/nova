"""Pipeline manager for coordinating processing phases."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from ..models.result import ProcessingResult
from ..config import PipelineConfig
from .phase import Phase
from .phase_runner import PhaseRunner


class PipelineManager:
    """Pipeline manager for coordinating processing phases."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize the pipeline manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.phase_runner = PhaseRunner(config)
        self.phases: List[Phase] = []
        
        # Initialize phases
        self._initialize_phases()
    
    def _initialize_phases(self) -> None:
        """Initialize processing phases from configuration."""
        for phase_name, phase_config in self.config.phases.items():
            try:
                phase = Phase(name=phase_name, config=phase_config)
                self.phases.append(phase)
            except Exception as e:
                self.logger.error(f"Error initializing phase {phase_name}: {str(e)}")
    
    async def run(self, input_files: List[Path]) -> Dict[str, ProcessingResult]:
        """Run the pipeline on input files.
        
        Args:
            input_files: List of input files to process
            
        Returns:
            Dictionary mapping file paths to processing results
        """
        results = {}
        
        try:
            # Process each file through all phases
            for file_path in input_files:
                self.logger.info(f"Processing file: {file_path}")
                
                # Initialize context
                context = {
                    'input_file': file_path,
                    'phase_results': {}
                }
                
                # Run each phase
                for phase in self.phases:
                    try:
                        result = await phase.process(file_path, context)
                        context['phase_results'][phase.name] = result
                        
                        # Stop processing if phase failed
                        if not result.success:
                            self.logger.error(f"Phase {phase.name} failed for {file_path}")
                            break
                            
                    except Exception as e:
                        self.logger.error(f"Error in phase {phase.name} for {file_path}: {str(e)}")
                        break
                
                # Store final results
                results[str(file_path)] = context['phase_results']
                
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
        
        return results
    
    async def cleanup(self) -> None:
        """Clean up pipeline resources."""
        for phase in self.phases:
            try:
                await phase.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up phase {phase.name}: {str(e)}")
    
    def get_phase(self, name: str) -> Optional[Phase]:
        """Get a phase by name.
        
        Args:
            name: Phase name
            
        Returns:
            Phase instance if found, None otherwise
        """
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None 