"""Pipeline manager module."""

from pathlib import Path
from typing import Dict, Any, Optional

from ..config import PipelineConfig, ProcessorConfig
from ..logging import get_logger
from .base import BaseProcessor
from .processor import Pipeline

logger = get_logger(__name__)

class PipelineManager:
    """Manages the document processing pipeline."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize pipeline manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.processors: Dict[str, BaseProcessor] = {}
        self.phase_configs: Dict[str, ProcessorConfig] = {
            phase.name: phase for phase in config.phases
        }
        
    def register_processor(self, phase: str, processor: BaseProcessor):
        """Register a processor for a phase.
        
        Args:
            phase: Phase name
            processor: Processor instance
        """
        if phase not in self.phase_configs:
            raise ValueError(f"Invalid phase: {phase}")
        self.processors[phase] = processor
        
    async def run(self) -> bool:
        """Run pipeline.
        
        Returns:
            True if pipeline completed successfully, False otherwise
        """
        try:
            # Create pipeline
            pipeline = Pipeline(self.config)
            
            # Register phases
            for phase, processor in self.processors.items():
                pipeline.register_phase(phase, processor)
            
            # Run pipeline
            success = await pipeline.run()
            if not success:
                logger.error("Pipeline failed")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to run pipeline: {str(e)}")
            return False 