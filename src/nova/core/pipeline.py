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
            self.console.print(f"[dim][DEBUG][/dim] {message}")
            
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
            phases: List of phases to run (default: all phases)
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        # Get phases from config if not specified
        if phases is None:
            phases = self.config.pipeline.phases
            
        # Track phase durations
        phase_durations = {}
        
        # Process each phase
        for phase in phases:
            try:
                # Get phase instance
                phase_instance = self.get_phase_instance(phase)
                if not phase_instance:
                    self.logger.error(f"Invalid phase: {phase}")
                    continue
                
                # Get files to process
                files = []
                if phase == "parse":
                    # For parse phase, look in input directory
                    for file_path in directory.rglob('*'):
                        if file_path.is_file():
                            files.append(file_path)
                elif phase == "disassemble":
                    # For disassemble phase, look in parse phase output directory
                    parse_dir = self.config.processing_dir / "phases" / "parse"
                    if parse_dir.exists():
                        for file_path in parse_dir.rglob('*.parsed.md'):
                            if file_path.is_file():
                                files.append(file_path)
                elif phase == "split":
                    # For split phase, look in disassemble phase output directory
                    disassemble_dir = self.config.processing_dir / "phases" / "disassemble"
                    if disassemble_dir.exists():
                        for file_path in disassemble_dir.rglob('*'):
                            if file_path.is_file():
                                files.append(file_path)
                elif phase == "finalize":
                    # For finalize phase, look in split directory
                    split_dir = self.config.processing_dir / "phases" / "split"
                    if split_dir.exists():
                        main_files = ["Summary.md", "Raw Notes.md", "Attachments.md"]
                        for file_name in main_files:
                            file_path = split_dir / file_name
                            if file_path.is_file():
                                files.append(file_path)
                
                # Start phase tracking
                await self.progress_tracker.add_phase(phase, len(files))
                phase_start_time = time.time()
                
                if not files:
                    self.logger.info(f"No files found for {phase} phase")
                    continue
                
                # Process each file
                for file_path in files:
                    # Start file tracking
                    await self.progress_tracker.start_file(file_path)
                    await self.progress_tracker.start_phase(phase, file_path)
                    
                    try:
                        # Check if file needs reprocessing
                        if phase != "finalize":
                            needs_reprocess = await self.needs_reprocessing(file_path, phase)
                            if not needs_reprocess:
                                self.debug(f"File unchanged: {file_path}")
                                self.state[phase]['unchanged_files'].add(file_path)
                                await self.progress_tracker.complete_phase(phase, file_path)
                                await self.progress_tracker.complete_file(file_path)
                                continue
                            else:
                                self.debug(f"File needs reprocessing: {file_path}")
                                self.state[phase]['reprocessed_files'].add(file_path)
                        
                        # Process file
                        output_dir = self.get_phase_output_dir(phase)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        metadata = await phase_instance.process_file(file_path, output_dir)
                        if metadata:
                            self.state[phase]['successful_files'].add(file_path)
                            await self.progress_tracker.complete_phase(phase, file_path)
                        else:
                            self.state[phase]['failed_files'].add(file_path)
                            await self.progress_tracker.fail_phase(phase, file_path)
                        
                        await self.progress_tracker.complete_file(file_path)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process {file_path}: {str(e)}")
                        self.logger.error(traceback.format_exc())
                        self._add_failed_file(phase, file_path, str(e))
                        await self.progress_tracker.fail_phase(phase, file_path)
                        await self.progress_tracker.fail_file(file_path)
                
                # Finalize phase
                try:
                    phase_instance.finalize()
                except Exception as e:
                    self.logger.error(f"Error in {phase} finalize: {str(e)}")
                    self.logger.error(traceback.format_exc())
                
                # Store phase duration
                phase_durations[phase] = time.time() - phase_start_time
                
            except Exception as e:
                self.logger.error(f"Error in {phase} phase: {str(e)}")
                continue
        
        # Print final summary
        self.progress_tracker.print_summary()

    async def needs_reprocessing(self, file_path: Path, phase: str) -> bool:
        """Return True if file needs reprocessing.
        Only the parse phase checks for actual changes - other phases always process.
        """
        # Skip .DS_Store files
        if file_path.name == ".DS_Store":
            return False
            
        # Split and finalize phases always process
        if phase != "parse":
            return True
            
        processing_dir = self.config.processing_dir
        phases_dir = Path(processing_dir) / "phases"
        logger.debug(f"Checking if {file_path} needs reprocessing in {processing_dir}")

        # Get relative path from input directory
        input_dir = Path(self.config.input_dir)
        try:
            rel_path = file_path.relative_to(input_dir)
        except ValueError:
            logger.error(f"File {file_path} is not under input directory {input_dir}")
            return True

        # If the user's input file or directory isn't valid, assume we need reprocessing
        if not file_path.exists():
            logger.info(f"Input file {file_path} doesn't exist - will process when it appears")
            return True

        # For markdown files in the root directory, look in the root output directory
        if file_path.suffix.lower() == '.md' and len(rel_path.parts) == 1:
            output_path = phases_dir / phase / f"{file_path.stem}.parsed.md"
        else:
            # For all other files, preserve the directory structure
            output_path = phases_dir / phase / rel_path.parent / f"{file_path.stem}.parsed.md"
        logger.debug(f"Checking parse output: {output_path}")
        
        # If .parsed.md file doesn't exist => must reprocess
        if not output_path.exists():
            logger.info(f"No previous output found for {file_path.name} - will process")
            return True
        
        # Check if we're doing a clean run by checking if the phases directory was just created
        try:
            phases_dir_mtime = phases_dir.stat().st_mtime
            current_time = time.time()
            if current_time - phases_dir_mtime < 60:  # If phases directory was created in the last minute
                logger.info(f"Clean run detected - will reprocess {file_path.name}")
                return True
        except OSError as e:
            logger.error(f"Error checking phases directory time: {str(e)}")
            return True
        
        # Check if input is newer than output
        try:
            input_mtime = file_path.stat().st_mtime
            output_mtime = output_path.stat().st_mtime
            logger.debug(f"Comparing timestamps for {file_path.name}")
            
            # Get formatted timestamps for logging
            input_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(input_mtime))
            output_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(output_mtime))
            
            if output_mtime < input_mtime:
                logger.info(f"File {file_path.name} modified ({input_time}) after last processing ({output_time}) - will reprocess")
                return True
            else:
                logger.info(f"File {file_path.name} unchanged since last processing ({output_time}) - skipping")
                return False
        except OSError as e:
            logger.error(f"Error checking file times: {str(e)}")
            return True
        
        return False

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

    async def _process_file(self, phase: Phase, file_path: Path) -> Optional[FileMetadata]:
        """Process a file with a phase.
        
        Args:
            phase: Phase to process file with.
            file_path: Path to file to process.
            
        Returns:
            Document metadata if successful, None otherwise.
        """
        try:
            # Get output directory for phase
            output_dir = self.get_phase_output_dir(phase.name)
            
            # Process file
            metadata = await phase.process(file_path, output_dir)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to process {file_path} with {phase.name}: {str(e)}")
            return None 

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
                    await phase.process(file_path, output_dir)
                except Exception as e:
                    logger.error(f"Failed to process {file_path} in {phase_name} phase: {e}")
                    logger.error(traceback.format_exc())
            
            # Finalize phase
            try:
                phase.finalize()
            except Exception as e:
                logger.error(f"Failed to finalize {phase_name} phase: {e}")
                logger.error(traceback.format_exc())
            
            # Print phase summary
            duration = time.time() - start_time
            phase.print_summary()
            logger.info(f"{phase_name} phase completed in {duration:.2f}s") 