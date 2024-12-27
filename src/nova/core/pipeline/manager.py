"""Pipeline manager for processing phases."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import importlib
import os
import shutil
import traceback
import re
import inspect

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..utils.metrics import MetricsTracker
from ..utils.monitoring import MonitoringManager
from ..utils.error_tracker import ErrorTracker
from ..console.logger import ConsoleLogger
from ..console.color_scheme import ColorScheme
from .phase_runner import PhaseRunner
from .pipeline_reporter import PipelineReporter
from ..config.base import ProcessorConfig, PipelineConfig, PathConfig


class PipelineManager:
    """Manager for processing pipeline phases."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the pipeline manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Extract pipeline configuration
        if isinstance(self.config, dict):
            if 'pipeline' in self.config:
                self.pipeline_config = self.config['pipeline']
            else:
                self.pipeline_config = self.config
        else:
            # Handle PipelineConfig object
            self.pipeline_config = self.config.model_dump()
        
        # Initialize core components
        self.logger = ConsoleLogger()
        self.metrics = MetricsTracker()
        self.monitor = MonitoringManager()
        self.error_tracker = ErrorTracker()
        self.color_scheme = ColorScheme()
        
        # Initialize state
        self.state = {
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': []
        }
        
        # Initialize pipeline components with logger
        self.phase_runner = PhaseRunner(
            config=self.pipeline_config,
            timing=None,  # Will be created by PhaseRunner
            metrics=self.metrics,
            logger=self.logger,
            color_scheme=self.color_scheme
        )
        
        self.reporter = PipelineReporter(
            logger=self.logger,
            color_scheme=self.color_scheme
        )
        
    async def cleanup(self) -> None:
        """Clean up resources and temporary files."""
        try:
            # Get paths from config
            if isinstance(self.pipeline_config, dict):
                paths = self.pipeline_config.get('paths', {})
            else:
                paths = self.pipeline_config.paths
            
            # Clean up temporary files
            temp_dir = self._expand_env_vars(paths.temp_dir if isinstance(paths, PathConfig) else paths.get('temp_dir', ''))
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                
            # Clean up processing directories
            processing_dir = self._expand_env_vars(paths.processing_dir if isinstance(paths, PathConfig) else paths.get('processing_dir', ''))
            if processing_dir and os.path.exists(processing_dir):
                for item in os.listdir(processing_dir):
                    item_path = os.path.join(processing_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.unlink(item_path)
                        
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            
    def _expand_env_vars(self, value: str) -> str:
        """Expand environment variables in a string value.
        
        Args:
            value: String value to expand
            
        Returns:
            String with environment variables expanded
        """
        if not isinstance(value, str):
            return value
            
        # Find all environment variables
        env_vars = re.findall(r'\${([^}]+)}', value)
        
        # Replace each variable
        result = value
        for var in env_vars:
            env_value = os.environ.get(var)
            if env_value is None:
                self.logger.warning(f"Environment variable {var} not found")
                continue
            result = result.replace('${' + var + '}', env_value)
            
        return result
        
    async def __aenter__(self) -> 'PipelineManager':
        """Enter async context."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.cleanup()
        
    async def run(self) -> bool:
        """Run the pipeline phases.
        
        Returns:
            bool: True if pipeline completed successfully
        """
        try:
            # Start pipeline
            self.logger.info("Starting pipeline execution")
            
            # Get phases from config
            if isinstance(self.pipeline_config, dict):
                phases = self.pipeline_config.get('phases', {})
            else:
                phases = self.pipeline_config.phases
            
            # Convert phases list to dictionary if needed
            if isinstance(phases, list):
                phases_dict = {}
                for phase in phases:
                    if isinstance(phase, dict):
                        phases_dict.update(phase)
                phases = phases_dict
            
            total_phases = len(phases)
            self.reporter.start_pipeline(total_phases)
            
            # Process each phase
            for phase_name, phase_config in phases.items():
                try:
                    # Start phase
                    self.logger.info(f"Starting phase: {phase_name}")
                    
                    # Convert phase config to ProcessorConfig if needed
                    if not isinstance(phase_config, ProcessorConfig):
                        phase_config = ProcessorConfig(**phase_config)
                    
                    # Get input files
                    input_dir = self._expand_env_vars(phase_config.input_dir or '')
                    input_dir = Path(input_dir)
                    if not input_dir.exists():
                        self.logger.warning(f"Input directory not found: {input_dir}")
                        continue
                        
                    # Count files to process
                    file_patterns = phase_config.components.get('file_patterns', ['*'])
                    if not isinstance(file_patterns, list):
                        file_patterns = [file_patterns]
                        
                    total_files = 0
                    for pattern in file_patterns:
                        total_files += sum(1 for _ in input_dir.rglob(pattern))
                    
                    # Start phase processing
                    self.phase_runner.start_phase(phase_name, total_files)
                    
                    # Process files
                    processed = 0
                    for pattern in file_patterns:
                        for file_path in input_dir.rglob(pattern):
                            try:
                                # Process file
                                await self._process_file(file_path, phase_config)
                                processed += 1
                                
                                # Update progress
                                self.phase_runner.update_progress(
                                    files_processed=processed,
                                    total_files=total_files
                                )
                                
                            except Exception as e:
                                self.logger.error(f"Error processing {file_path}: {str(e)}")
                                self.state['failed_files'] += 1
                                self.state['errors'].append(str(e))
                                
                    # End phase
                    self.phase_runner.end_phase(phase_name)
                    
                except Exception as e:
                    self.logger.error(f"Phase {phase_name} failed: {str(e)}")
                    self.state['errors'].append(str(e))
                    continue
                    
            # End pipeline
            self.reporter.end_pipeline()
            
            # Check for errors
            if self.state['errors']:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            return False
            
    async def _process_file(self, file_path: Path, phase_config: Dict[str, Any]) -> None:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            phase_config: Phase configuration
        """
        try:
            # Convert phase config to ProcessorConfig if needed
            if not isinstance(phase_config, ProcessorConfig):
                phase_config = ProcessorConfig(**phase_config)
            
            # Get processor class
            processor_path = phase_config.processor
            if not processor_path:
                raise ValueError(f"No processor specified for file: {file_path}")
                
            # Import processor
            module_path, class_name = processor_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            processor_class = getattr(module, class_name)
            
            # Create processor instance with correct arguments
            processor = processor_class(
                processor_config=phase_config,
                pipeline_config=PipelineConfig(
                    paths=PathConfig(base_dir=self._expand_env_vars(phase_config.output_dir)),
                    phases=[phase_config],
                    input_dir=self._expand_env_vars(phase_config.input_dir or ''),
                    output_dir=self._expand_env_vars(phase_config.output_dir),
                    processing_dir=self._expand_env_vars(phase_config.output_dir),
                    temp_dir=self._expand_env_vars(phase_config.output_dir)
                ),
                timing=None,  # Will be created by processor
                metrics=self.metrics,
                console=Console()
            )
            
            # Get output directory
            output_dir = self._expand_env_vars(phase_config.output_dir)
            if not output_dir:
                raise ValueError(f"No output directory specified for phase")
            
            # Create context with output directory
            context = {'output_dir': Path(output_dir)}
            
            # Process file
            result = await processor.process(file_path, context)
            if result.success:
                self.state['processed_files'] += 1
            else:
                self.state['failed_files'] += 1
                if result.errors:
                    for error in result.errors:
                        self.logger.error(f"Error processing {file_path}: {error}")
                        self.state['errors'].append(error)
                else:
                    error_msg = f"Unknown error processing {file_path}"
                    self.logger.error(error_msg)
                    self.state['errors'].append(error_msg)
                raise ValueError(result.errors[0] if result.errors else "Unknown error")
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            self.state['failed_files'] += 1
            self.state['errors'].append(str(e))
            raise 