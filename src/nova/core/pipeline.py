from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from .config import PipelineConfig
from .logging import get_logger
from .pipeline.base import BaseProcessor

logger = get_logger(__name__)

class PipelineManager:
    """Manages the document processing pipeline."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize pipeline manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.processors = {}
        
    def register_processor(self, phase: str, processor: BaseProcessor):
        """Register a processor for a phase.
        
        Args:
            phase: Phase name
            processor: Processor instance
        """
        if phase not in self.config.phases:
            raise ValueError(f"Invalid phase: {phase}")
        self.processors[phase] = processor
        
    async def run(self) -> bool:
        """Run the pipeline.
        
        Returns:
            True if all phases completed successfully, False otherwise
        """
        try:
            # Set up all processors
            for phase in self.config.phases:
                processor = self.processors.get(phase)
                if not processor:
                    logger.error(f"No processor registered for phase: {phase}")
                    return False
                    
                await processor.setup()
                
            # Run each phase
            for phase in self.config.phases:
                processor = self.processors[phase]
                logger.info(f"Running phase: {phase}")
                
                success = await processor.process()
                if not success:
                    logger.error(f"Error in phase {phase}")
                    return False
                    
            # Clean up
            for processor in self.processors.values():
                await processor.cleanup()
                
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            return False 