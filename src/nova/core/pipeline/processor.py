"""Pipeline processor classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ..config import ProcessorConfig, PipelineConfig
from ..logging import get_logger
from ..errors import ProcessorError
from .base import BaseProcessor
from .phase import PipelinePhase
from .types import PhaseDefinition, PhaseType

logger = get_logger(__name__)

class Pipeline:
    """Document processing pipeline."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.phases: Dict[str, PipelinePhase] = {}
        
    def register_phase(self, name: str, processor: BaseProcessor):
        """Register a phase.
        
        Args:
            name: Phase name
            processor: Phase processor
        """
        # Create phase definition
        definition = PhaseDefinition(
            name=name,
            description=f"Phase {name}",
            type=PhaseType(name),  # Convert name to PhaseType
            output_dir=processor.output_dir,
            processor=processor.__class__.__name__,
            components=processor.components
        )
        
        # Create phase
        self.phases[name] = PipelinePhase(
            definition=definition,
            processor_config=processor.processor_config,
            pipeline_config=self.config
        )
        
    async def run(self) -> bool:
        """Run pipeline.
        
        Returns:
            True if pipeline completed successfully, False otherwise
        """
        try:
            # Set up phases
            for phase in self.phases.values():
                await phase.processor.setup()
            
            # Process phases
            for phase in self.phases.values():
                success = await phase.processor.process()
                if not success:
                    logger.error(f"Phase {phase.name} failed")
                    return False
            
            # Clean up phases
            for phase in self.phases.values():
                await phase.processor.cleanup()
                
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            return False

# Additional processor implementations can be added here 