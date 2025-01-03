"""Nova pipeline implementation."""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from nova.config.manager import ConfigManager
from nova.config.settings import PipelineConfig
from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from nova.phases.parse import ParsePhase
from nova.phases.disassemble import DisassemblyPhase
from nova.phases.split import SplitPhase
from nova.phases.finalize import FinalizePhase
from nova.core.logging import print_summary
from nova.core.progress import ProgressTracker
from nova.utils.output_manager import OutputManager

logger = logging.getLogger(__name__)
console = Console()

class NovaPipeline:
    """Pipeline for processing files."""
    
    def __init__(self, config: ConfigManager):
        """Initialize pipeline.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        
        # Initialize output manager
        self.output_manager = OutputManager(config)
        
        # Initialize state
        self.state = PipelineConfig.create_initial_state()
        self.error_messages: Dict[str, Dict[Path, str]] = {}
        
        # Initialize progress tracker
        self.progress_tracker = ProgressTracker()
        
        # Initialize phases
        self.phases = {
            "parse": ParsePhase(config, self),
            "disassemble": DisassemblyPhase(config, self),
            "split": SplitPhase(config, self),
            "finalize": FinalizePhase(config, self)
        }
        
        # Reset state after phases are initialized
        self.reset_state()
        
    def debug(self, message: str) -> None:
        """Print debug message if debug logging is enabled.
        
        Args:
            message: Message to print
        """
        if os.getenv('NOVA_LOG_LEVEL', '').upper() == 'DEBUG':
            self.logger.debug(message)
            
    def reset_state(self) -> None:
        """Reset pipeline state."""
        self.state = PipelineConfig.create_initial_state()
        
    def _add_failed_file(self, phase: str, file_path: Path, error_msg: str) -> None:
        """Add a file to the failed files set with its error message.
        
        Args:
            phase: Phase name
            file_path: Path to failed file
            error_msg: Error message
        """
        self.state[phase]['failed_files'].add(file_path)
        if phase not in self.error_messages:
            self.error_messages[phase] = {}
        self.error_messages[phase][file_path] = error_msg
        
    async def process_directory(self, directory: Union[str, Path], phases: List[str] = None) -> None:
        """Process all files in a directory.
        
        Args:
            directory: Directory to process
            phases: Optional list of phases to run. If None, runs all phases.
        """
        try:
            # Convert directory to Path
            directory = Path(directory)
            
            # Get phases to run
            if phases is None:
                phases = self.config.pipeline.phases
                
            # Track phase durations
            phase_durations = {}
            
            # Process each phase
            for phase_name in phases:
                try:
                    # Get phase instance
                    phase_instance = self.get_phase_instance(phase_name)
                    if not phase_instance:
                        self.logger.error(f"Phase not found: {phase_name}")
                        continue
                        
                    # Initialize phase state
                    self._init_phase_state(phase_name)
                    
                    # Track validation status for finalize phase
                    validation_passed = True
                    
                    # Get files to process based on phase
                    files = []
                    if phase_name == "parse":
                        # For parse phase, look in input directory
                        for file_path in directory.rglob('*'):
                            if file_path.is_file():
                                # Skip hidden files and directories
                                if not any(part.startswith('.') for part in file_path.parts):
                                    files.append(file_path)
                    elif phase_name == "disassemble":
                        # For disassemble phase, look in parse phase output directory
                        parse_dir = self.config.processing_dir / "phases" / "parse"
                        if parse_dir.exists():
                            for file_path in parse_dir.rglob('*.parsed.md'):
                                if file_path.is_file():
                                    files.append(file_path)
                    elif phase_name == "split":
                        # For split phase, look in disassemble phase output directory
                        disassemble_dir = self.config.processing_dir / "phases" / "disassemble"
                        if disassemble_dir.exists():
                            for file_path in disassemble_dir.rglob('*.summary.md'):
                                if file_path.is_file():
                                    files.append(file_path)
                    elif phase_name == "finalize":
                        # For finalize phase, look in split directory
                        split_dir = self.config.processing_dir / "phases" / "split"
                        if split_dir.exists():
                            main_files = ["Summary.md", "Raw Notes.md", "Attachments.md"]
                            for file_name in main_files:
                                file_path = split_dir / file_name
                                if file_path.is_file():
                                    files.append(file_path)
                    
                    # Start phase tracking
                    await self.progress_tracker.add_phase(phase_name, len(files))
                    phase_start_time = time.time()
                    
                    if not files:
                        self.logger.info(f"No files found for {phase_name} phase")
                        continue
                    
                    # Process each file
                    for file_path in files:
                        # Start file tracking
                        await self.progress_tracker.start_file(file_path)
                        await self.progress_tracker.start_phase(phase_name, file_path)
                        
                        try:
                            # Check if file needs reprocessing
                            if phase_name != "finalize":
                                needs_reprocess = await self.needs_reprocessing(file_path, phase_name)
                                if not needs_reprocess:
                                    self.debug(f"File unchanged: {file_path}")
                                    self.state[phase_name]['unchanged_files'].add(file_path)
                                    await self.progress_tracker.complete_phase(phase_name, file_path)
                                    await self.progress_tracker.complete_file(file_path)
                                    continue
                                else:
                                    self.debug(f"File needs reprocessing: {file_path}")
                                    self.state[phase_name]['reprocessed_files'].add(file_path)
                            
                            # Process file
                            output_dir = self.get_phase_output_dir(phase_name)
                            output_dir.mkdir(parents=True, exist_ok=True)
                            
                            metadata = await phase_instance.process_file(file_path, output_dir)
                            if metadata:
                                self.state[phase_name]['successful_files'].add(file_path)
                                await self.progress_tracker.complete_phase(phase_name, file_path)
                            else:
                                self.state[phase_name]['failed_files'].add(file_path)
                                await self.progress_tracker.fail_phase(phase_name, file_path)
                            
                            await self.progress_tracker.complete_file(file_path)
                            
                        except Exception as e:
                            self.logger.error(f"Failed to process {file_path} in {phase_name} phase: {str(e)}")
                            self.logger.error(traceback.format_exc())
                            self._add_failed_file(phase_name, file_path, str(e))
                            await self.progress_tracker.fail_phase(phase_name, file_path)
                            await self.progress_tracker.fail_file(file_path)
                    
                    # Finalize phase
                    try:
                        phase_instance.finalize()
                    except Exception as e:
                        self.logger.error(f"Error in {phase_name} finalize: {str(e)}")
                        self.logger.error(traceback.format_exc())
                        # Add error to phase state
                        self._add_failed_file(phase_name, Path("finalize"), str(e))
                        # Update progress tracker
                        await self.progress_tracker.fail_phase(phase_name, Path("finalize"), str(e))
                        # Mark validation as failed
                        validation_passed = False
                    
                    # Store phase duration
                    phase_durations[phase_name] = time.time() - phase_start_time
                    
                except Exception as e:
                    self.logger.error(f"Error in {phase_name} phase: {str(e)}")
                    continue
            
            # Print final summary
            await self.progress_tracker.print_summary()
            
        except Exception as e:
            self.logger.error(f"Failed to process directory {directory}: {str(e)}")
            self.logger.error(traceback.format_exc())
        
    async def needs_reprocessing(self, file_path: Path, phase: str) -> bool:
        """Check if a file needs to be reprocessed.
        
        Args:
            file_path: Path to file to check
            phase: Phase to check for
            
        Returns:
            True if file needs reprocessing, False otherwise
        """
        # Always reprocess in finalize phase
        if phase == "finalize":
            return True
            
        # Get output file path
        output_dir = self.get_phase_output_dir(phase)
        output_file = output_dir / file_path.name
        
        # If output doesn't exist, needs reprocessing
        if not output_file.exists():
            return True
            
        # Check if input is newer than output
        input_mtime = file_path.stat().st_mtime
        output_mtime = output_file.stat().st_mtime
        
        return input_mtime > output_mtime
        
    def get_phase_output_dir(self, phase: str) -> Path:
        """Get the output directory for a phase."""
        return self.config.processing_dir / "phases" / phase
        
    def get_phase_instance(self, phase_name: str) -> Optional[Phase]:
        """Get phase instance by name.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Phase instance or None if invalid phase
        """
        phase_map = {
            'parse': ParsePhase,
            'disassemble': DisassemblyPhase,
            'split': SplitPhase,
            'finalize': FinalizePhase
        }
        
        phase_class = phase_map.get(phase_name)
        if phase_class:
            return phase_class(self.config, self)
        return None
        
    def get_phases(self) -> List[str]:
        """Get list of available phases in order.
        
        Returns:
            List of phase names in execution order
        """
        return ["parse", "disassemble", "split", "finalize"]
        
    async def process_files(self, files: List[Path]) -> None:
        """Process a list of files through all phases.
        
        Args:
            files: List of files to process
        """
        total_files = len(files)
        processed_files = 0
        
        # Process each file through each phase
        for phase_name, phase in self.phases.items():
            logger.info(f"\nStarting {phase_name} phase")
            start_time = time.time()
            
            # Process each file
            for file_path in files:
                processed_files += 1
                
                # Only log every 10th file or when it's being processed
                if processed_files % 10 == 0:
                    logger.info(f"Processing file {processed_files}/{total_files}: {file_path.name}")
                
                # Get output directory for this phase
                output_dir = self.config.processing_dir / "phases" / phase_name
                output_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Process file
                    await phase.process_file(file_path, output_dir)
                except Exception as e:
                    logger.error(f"Failed to process {file_path} in {phase_name} phase: {e}")
                    logger.error(traceback.format_exc())
            
            # Finalize phase
            try:
                phase.finalize()
            except Exception as e:
                logger.error(f"Failed to finalize {phase_name} phase: {e}")
                logger.error(traceback.format_exc())
                
        # Print final summary
        await self.progress_tracker.print_summary()

    def _init_phase_state(self, phase_name: str) -> None:
        """Initialize state for a phase.
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name not in self.state:
            self.state[phase_name] = {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'file_type_stats': {}
            } 

    async def process_phase(self, phase_name: str) -> bool:
        """Process a single phase.
        
        Args:
            phase_name: Name of phase to process
            
        Returns:
            Whether phase completed successfully
        """
        phase = self.phases[phase_name]
        total_files = len(phase.get_input_files())
        processed = 0
        
        try:
            # Initialize phase state
            self._init_phase_state(phase_name)
            
            # Process each file
            for file_path in phase.get_input_files():
                try:
                    await phase.process_file(file_path)
                    processed += 1
                except Exception as e:
                    self.logger.error(f"Error processing {file_path} in {phase_name}: {str(e)}")
                    self.error_messages[phase_name][file_path] = str(e)
                    continue
            
            # Finalize phase
            await phase.finalize()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in {phase_name} phase: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False 