"""Pipeline module for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import os

from .config import PipelineConfig, ProcessorConfig
from .logging import get_logger

logger = get_logger(__name__)

class BaseProcessor:
    """Base processor class."""
    
    def __init__(self, processor_config: Union[ProcessorConfig, Dict[str, Any]], pipeline_config: PipelineConfig):
        """Initialize base processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        logger.debug(f"Initializing processor with config: {processor_config}")
        
        # Create processor config if needed
        if not isinstance(processor_config, ProcessorConfig):
            try:
                processor_config = ProcessorConfig(
                    name=processor_config.get('name', 'unknown'),
                    description=processor_config.get('description', 'Unknown processor'),
                    output_dir=processor_config['output_dir'],
                    processor=processor_config.get('processor', 'UnknownProcessor'),
                    enabled=processor_config.get('enabled', True),
                    components=processor_config.get('components', {}),
                    handlers=processor_config.get('handlers', [])
                )
                logger.debug(f"Created processor config: {processor_config}")
            except Exception as e:
                logger.error(f"Failed to create processor config: {e}")
                logger.debug(f"Config data: {processor_config}")
                raise
        
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.output_dir = Path(processor_config.output_dir)
        
        # Set up components
        self.components: Dict[str, Any] = {}
        if processor_config.components is not None:
            self.components = processor_config.components
        
    async def setup(self) -> None:
        """Set up processor."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def process(self) -> bool:
        """Process files.
        
        Returns:
            True if processing completed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement process()")
        
    async def cleanup(self) -> None:
        """Clean up processor."""
        pass

class PipelinePhase:
    """Pipeline phase."""
    
    def __init__(self, name: str, processor: BaseProcessor):
        """Initialize pipeline phase.
        
        Args:
            name: Phase name
            processor: Phase processor
        """
        self.name = name
        self.processor = processor

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
        self.phases[name] = PipelinePhase(name, processor)
        
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