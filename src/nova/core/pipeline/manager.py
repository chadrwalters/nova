"""Pipeline manager module."""

from pathlib import Path
from typing import Dict, Any, Optional

from ..config import PipelineConfig, ProcessorConfig
from ..logging import get_logger
from .base import BaseProcessor
from .processor import Pipeline
from ..utils.schema_validator import SchemaValidator

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
        self.schema_validator = SchemaValidator()
        
    def register_processor(self, phase: str, processor: BaseProcessor):
        """Register a processor for a phase.
        
        Args:
            phase: Phase name
            processor: Processor instance
        """
        if phase not in self.phase_configs:
            raise ValueError(f"Invalid phase: {phase}")
        self.processors[phase] = processor
        
    async def load_config(self, config: Dict[str, Any]) -> None:
        """Load pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
        """
        # Validate configuration
        self.schema_validator.validate_config(config)
        
        # Extract pipeline config
        pipeline_config = config.get('pipeline', {})
        paths = pipeline_config.get('paths', {})
        
        # Ensure base_dir is set
        if 'base_dir' not in paths:
            paths['base_dir'] = "${NOVA_BASE_DIR}"
            
        phases = []
        
        # Process phases
        for phase_dict in pipeline_config.get('phases', []):
            for name, phase_config in phase_dict.items():
                phase_config['name'] = name
                phases.append(ProcessorConfig(**phase_config))
        
        # Create new config
        self.config = PipelineConfig(paths=paths, phases=phases)
        self.phase_configs = {
            phase.name: phase for phase in self.config.phases
        }
        
    def get_validation_report(self) -> Dict[str, Any]:
        """Get validation report from schema validator.
        
        Returns:
            Dictionary containing validation results
        """
        return self.schema_validator.get_validation_report()
        
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