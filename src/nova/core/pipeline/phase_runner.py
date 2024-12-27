"""Phase runner for executing pipeline phases."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import importlib
import os
from datetime import datetime

from ..config import PipelineConfig, ProcessorConfig
from ..models.result import ProcessingResult
from ..utils.metrics import MetricsTracker
from ..utils.timing import TimingManager
from ..console.logger import ConsoleLogger
from ..console.color_scheme import ColorScheme


class PhaseRunner:
    """Runs individual pipeline phases."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        logger: Optional[ConsoleLogger] = None,
        color_scheme: Optional[ColorScheme] = None
    ):
        """Initialize the phase runner.
        
        Args:
            config: Pipeline configuration
            timing: Optional timing manager
            metrics: Optional metrics tracker
            logger: Optional console logger
            color_scheme: Optional color scheme
        """
        self.config = config
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.logger = logger or ConsoleLogger()
        self.color_scheme = color_scheme or ColorScheme()
        self.base_logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize state
        self.current_phase = None
        self.phase_stats = {}
        
    def start_phase(self, phase_name: str, total_files: int = 0) -> None:
        """Start a new processing phase.
        
        Args:
            phase_name: Name of the phase to start
            total_files: Total number of files to process
        """
        self.current_phase = phase_name
        self.phase_stats[phase_name] = {
            'start_time': datetime.now(),
            'total_files': total_files,
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': []
        }
        
        # Start phase timing
        self.timing.start_timer(f"phase_{phase_name}")
        
        # Log phase start
        self.logger.info(f"Starting phase: {phase_name}")
        if total_files > 0:
            self.logger.info(f"Files to process: {total_files}")
        
    def update_progress(self, files_processed: int, total_files: int) -> None:
        """Update phase progress.
        
        Args:
            files_processed: Number of files processed
            total_files: Total number of files
        """
        if not self.current_phase:
            return
            
        stats = self.phase_stats[self.current_phase]
        stats['processed_files'] = files_processed
        stats['total_files'] = total_files
        
        # Calculate progress percentage
        progress = (files_processed / total_files) * 100 if total_files > 0 else 0
        self.logger.info(f"Progress: {progress:.1f}% ({files_processed}/{total_files} files)")
        
    def end_phase(self, phase_name: str) -> None:
        """End a processing phase.
        
        Args:
            phase_name: Name of the phase to end
        """
        if phase_name != self.current_phase:
            raise ValueError(f"Cannot end phase {phase_name}, current phase is {self.current_phase}")
            
        # Stop phase timing
        duration = self.timing.stop_timer(f"phase_{phase_name}")
        
        # Update phase stats
        stats = self.phase_stats[phase_name]
        stats['end_time'] = datetime.now()
        stats['duration'] = duration
        
        # Log phase completion
        self.logger.info(f"\nPhase {phase_name} completed:")
        self.logger.info(f"Duration: {duration:.2f}s")
        self.logger.info(f"Files processed: {stats['processed_files']}/{stats['total_files']}")
        self.logger.info(f"Files failed: {stats['failed_files']}")
        self.logger.info(f"Files skipped: {stats['skipped_files']}")
        
        if stats['errors']:
            self.logger.info("\nErrors:")
            for error in stats['errors']:
                self.logger.error(error)
                
        self.current_phase = None
    
    async def run_phase(self, phase_name: str, phase_config: ProcessorConfig) -> ProcessingResult:
        """Run a pipeline phase.
        
        Args:
            phase_name: Name of the phase to run
            phase_config: Configuration for the phase
            
        Returns:
            ProcessingResult containing phase results
        """
        try:
            # Start phase
            self.start_phase(phase_name)
            
            # Create processor instance
            processor = self._create_processor(phase_name, phase_config)
            
            # Run the phase
            result = await processor.process()
            
            # Update phase stats
            stats = self.phase_stats[phase_name]
            if result.success:
                stats['processed_files'] += 1
            else:
                stats['failed_files'] += 1
                stats['errors'].extend(result.errors)
            
            # End phase
            self.end_phase(phase_name)
            
            return result
            
        except Exception as e:
            self.base_logger.error(f"Error in phase {phase_name}: {str(e)}")
            return ProcessingResult(success=False, errors=[str(e)])
            
    def _create_processor(self, phase_name: str, phase_config: ProcessorConfig) -> Any:
        """Create a processor instance for a phase.
        
        Args:
            phase_name: Name of the phase
            phase_config: Configuration for the phase
            
        Returns:
            Processor instance
            
        Raises:
            ImportError: If processor module cannot be imported
            ValueError: If processor class cannot be found
        """
        try:
            # Import processor module
            module_path = phase_config.processor
            module_name, class_name = module_path.rsplit('.', 1)
            module = importlib.import_module(module_name)
            
            # Get processor class
            processor_class = getattr(module, class_name)
            if not processor_class:
                raise ValueError(f"Processor class not found: {class_name}")
                
            # Create processor instance with correct arguments
            processor = processor_class(
                processor_config=phase_config,
                pipeline_config=PipelineConfig(
                    paths=PathConfig(base_dir=phase_config.output_dir),
                    phases=[phase_config],
                    input_dir=phase_config.input_dir or '',
                    output_dir=phase_config.output_dir,
                    processing_dir=phase_config.output_dir,
                    temp_dir=phase_config.output_dir
                ),
                timing=self.timing,
                metrics=self.metrics,
                console=self.logger.console
            )
            
            return processor
            
        except Exception as e:
            raise ImportError(f"Error creating processor for phase {phase_name}: {str(e)}") 