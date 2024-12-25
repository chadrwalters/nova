"""Pipeline module for Nova document processor."""

from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseProcessor
from .manager import PipelineManager
from .phase import PipelinePhase
from .types import PhaseType

__all__ = [
    'BaseProcessor',
    'PipelineManager',
    'PipelinePhase',
    'PhaseType',
    'Pipeline'
]

class Pipeline:
    """High-level pipeline interface."""
    
    def __init__(self, config=None):
        """Initialize pipeline.
        
        Args:
            config: Optional pipeline configuration
        """
        self.manager = PipelineManager(config)
    
    def process(
        self,
        input_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        show_state: bool = False,
        scan: bool = False
    ) -> bool:
        """Process documents through the pipeline.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            force: Whether to force processing
            dry_run: Whether to show what would be done
            show_state: Whether to display current state
            scan: Whether to show directory structure
            
        Returns:
            bool: True if processing completed successfully
        """
        # Show state if requested
        if show_state:
            state = self.manager.get_state()
            print("\nPipeline State:")
            for phase, phase_state in state.items():
                print(f"\n{phase}:")
                print(f"  Name: {phase_state['name']}")
                print(f"  Description: {phase_state['description']}")
                print(f"  Status: {phase_state['state'].get('status', 'not started')}")
            return True
        
        # Show directory structure if requested
        if scan:
            print("\nDirectory Structure:")
            for phase_type in PhaseType:
                phase_dir = self.manager.config.paths.get_phase_dir(phase_type)
                if phase_dir:
                    print(f"\n{phase_type.name}:")
                    print(f"  {phase_dir}")
                    if phase_dir.exists():
                        for item in phase_dir.iterdir():
                            print(f"    {item.name}")
            return True
        
        # Show what would be done if dry run
        if dry_run:
            print("\nDry Run - Would process:")
            print(f"  Input: {input_dir}")
            print(f"  Output: {output_dir}")
            print("\nPhases:")
            for phase_type in PhaseType:
                phase = self.manager.phases[phase_type]
                print(f"  {phase.name}: {phase.description}")
            return True
        
        # Process documents
        return self.manager.run_pipeline(
            input_path=input_dir,
            output_path=output_dir,
            options={'force': force}
        )
