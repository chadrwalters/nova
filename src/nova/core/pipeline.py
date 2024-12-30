"""Nova pipeline implementation."""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import traceback
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from nova.config.manager import ConfigManager
from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from nova.phases.parse import ParsePhase
from nova.phases.split import SplitPhase
from nova.phases.finalize import FinalizePhase
from nova.core.logging import print_summary

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
        
        # Initialize empty state
        self.state = {}
        self.error_messages = {}  # Store error messages by file path
        
        # Initialize phases
        self.phases = {
            "parse": ParsePhase(self),
            "split": SplitPhase(self),
            "finalize": FinalizePhase(self)
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
        # Initialize standard state for parse phase
        self.state = {
            "parse": {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'file_type_stats': {}
            }
        }
        
        # Initialize custom state for split phase
        self.state["split"] = {
            'summary_sections': 0,
            'raw_notes_sections': 0,
            'attachments': 0,
            'skipped_files': set(),
            'failed_files': set(),
            'successful_files': set(),  # Keep this for pipeline compatibility
            'unchanged_files': set(),   # Keep this for pipeline compatibility
            'reprocessed_files': set()  # Keep this for pipeline compatibility
        }
        
        # Initialize finalize phase state
        self.state["finalize"] = {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set()
        }
        
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

    async def process_directory(self, directory: Path, phases: List[str] = None) -> None:
        """Process all files in directory through specified phases."""
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
            
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
            
        # Get list of phases to run
        if phases is None:
            phases = self.get_phases()
            
        # Store phase durations and file counts
        phase_durations = {}
        phase_file_counts = {}
            
        # Process each phase
        for phase in phases:
            phase_start_time = time.time()
            
            try:
                # Get phase instance
                phase_instance = self.get_phase_instance(phase)
                if not phase_instance:
                    self.logger.error(f"Invalid phase: {phase}")
                    continue
                    
                # Initialize phase state if needed
                if phase not in self.state:
                    self.state[phase] = {
                        'successful_files': set(),
                        'failed_files': set(),
                        'skipped_files': set(),
                        'unchanged_files': set(),
                        'reprocessed_files': set()
                    }
                
                # Get list of files based on phase
                files = []
                if phase == "parse":
                    # For parse phase, look in input directory
                    for file_path in directory.rglob('*'):
                        if file_path.is_file() and not file_path.name.startswith('.'):
                            files.append(file_path)
                elif phase == "split":
                    # For split phase, look in parse phase output directory
                    parse_dir = self.config.processing_dir / "phases" / "parse"
                    if parse_dir.exists():
                        # Only process main files (not in subdirectories)
                        for file_path in parse_dir.glob('*.parsed.md'):
                            if file_path.is_file():
                                files.append(file_path)
                elif phase == "finalize":
                    # For finalize phase, look in split directory
                    split_dir = self.config.processing_dir / "phases" / "split"
                    self.debug(f"Looking for files to finalize in: {split_dir}")
                    if split_dir.exists():
                        # Look for all main files in subdirectories
                        main_files = ["Summary.md", "Raw Notes.md", "Attachments.md"]
                        for file_name in main_files:
                            file_path = split_dir / file_name
                            if file_path.is_file():
                                self.debug(f"Found file to finalize: {file_path}")
                                files.append(file_path)
                    else:
                        self.debug(f"Split directory does not exist: {split_dir}")
                
                # Store the actual file count for this phase
                phase_file_counts[phase] = len(files)
                
                if not files:
                    if phase == "finalize":
                        self.debug("No files found in split directory to finalize")
                    else:
                        self.debug(f"No files found for {phase} phase")
                    continue
                
                # Process each file with progress bar
                with tqdm(total=len(files), desc=f"{phase.upper()} Phase", unit="files", leave=True, position=0) as pbar:
                    for file_path in files:
                        # Log file being processed
                        self.debug(f"Processing {file_path}")
                        
                        # Check if file needs reprocessing (skip for finalize phase)
                        if phase != "finalize":
                            needs_reprocess = await self.needs_reprocessing(file_path, phase)
                            if not needs_reprocess:
                                self.debug(f"File unchanged: {file_path}")
                                self.state[phase]['unchanged_files'].add(file_path)
                                pbar.update(1)
                                continue
                            else:
                                self.debug(f"File needs reprocessing: {file_path}")
                            
                        # Process file
                        try:
                            # Get output directory for phase
                            output_dir = self.get_phase_output_dir(phase)
                            self.debug(f"Output directory: {output_dir}")
                            
                            # Create output directory if it doesn't exist
                            output_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Process file
                            metadata = await phase_instance.process_file(file_path, output_dir)
                            if metadata:
                                self.state[phase]['successful_files'].add(file_path)
                            else:
                                self.state[phase]['failed_files'].add(file_path)
                                
                        except Exception as e:
                            self.logger.error(f"Failed to process {file_path}: {str(e)}")
                            self.logger.error(traceback.format_exc())
                            self._add_failed_file(phase, file_path, str(e))
                            
                        pbar.update(1)
                
                # Call finalize() on the phase after processing all files
                try:
                    phase_instance.finalize()
                except Exception as e:
                    self.logger.error(f"Error in {phase} finalize: {str(e)}")
                    self.logger.error(traceback.format_exc())
                        
                # Log phase completion
                self.debug(f"Completed {phase} phase")
                
                # Store phase duration
                phase_durations[phase] = time.time() - phase_start_time
                        
            except Exception as e:
                self.logger.error(f"Error in {phase} phase: {str(e)}")
                continue
                
        # Print final summary
        print("\nProcessing Summary")
        print("━" * 80)
        
        # Show summaries for each completed phase
        for phase in phases:
            total_files = phase_file_counts.get(phase, 0)  # Use actual file count for this phase
            successful = len(self.state[phase]['successful_files'])
            failed = len(self.state[phase]['failed_files'])
            skipped = len(self.state[phase]['skipped_files'])
            unchanged = len(self.state[phase]['unchanged_files'])
            reprocessed = len(self.state[phase]['reprocessed_files'])
            duration = phase_durations.get(phase, 0)
            
            print(f"\n{phase.upper()} Phase")
            print("━" * 80)
            
            if phase == "parse":
                # Get file type statistics
                file_type_stats = self.state[phase].get('file_type_stats', {})
                if file_type_stats:
                    # Get all unique file types
                    file_types = sorted(file_type_stats.keys())
                    
                    # Calculate column widths
                    type_width = max(max(len(ft) for ft in file_types), 4)  # min width of 4 for "Type"
                    stat_width = 10  # Fixed width for numbers
                    
                    # Print header
                    print("\nFile Type Statistics:")
                    header = "┏" + "━" * (type_width + 2) + "┳" + ("━" * (stat_width + 2) + "┳") * 3 + "━" * (stat_width + 2) + "┓"
                    print(header)
                    print(f"┃ {'Type'.ljust(type_width)} ┃" + 
                          f" {'Total'.center(stat_width)} ┃" +
                          f" {'Success'.center(stat_width)} ┃" +
                          f" {'Failed'.center(stat_width)} ┃" +
                          f" {'Skipped'.center(stat_width)} ┃")
                    divider = "┣" + "━" * (type_width + 2) + "╋" + ("━" * (stat_width + 2) + "╋") * 3 + "━" * (stat_width + 2) + "┫"
                    print(divider)
                    
                    # Print each file type's stats
                    for file_type in file_types:
                        stats = file_type_stats[file_type]
                        print(f"┃ {file_type.ljust(type_width)} ┃" +
                              f" {str(stats['total']).rjust(stat_width)} ┃" +
                              f" {str(stats['successful']).rjust(stat_width)} ┃" +
                              f" {str(stats['failed']).rjust(stat_width)} ┃" +
                              f" {str(stats['skipped']).rjust(stat_width)} ┃")
                    footer = "┗" + "━" * (type_width + 2) + "┻" + ("━" * (stat_width + 2) + "┻") * 3 + "━" * (stat_width + 2) + "┛"
                    print(footer)
                    print()
            
            # Print phase statistics
            print("Phase Statistics:")
            print("┏━━━━━━━━━━━━━┳━━━━━━━━┓")
            print("┃ Metric      ┃  Value ┃")
            print("┡━━━━━━━━━━━━━╇━━━━━━━━┩")
            print(f"│ Total Files │ {total_files:>6d} │")
            print(f"│ Processed   │ {successful:>6d} │")
            print(f"│ Failed      │ {failed:>6d} │")
            print(f"│ Skipped     │ {skipped:>6d} │")
            print(f"│ Unchanged   │ {unchanged:>6d} │")
            print(f"│ Reprocessed │ {reprocessed:>6d} │")
            print(f"│ Duration    │ {duration:>6.2f}s │")
            print("└─────────────┴────────┘")
            
            # Print list of failed files and their errors if any
            if failed > 0:
                print("\nFailed files:")
                print("━" * 80)
                for f in sorted(self.state[phase]['failed_files']):
                    error_msg = self.error_messages.get(phase, {}).get(f, 'Unknown error')
                    print(f"• {f.name}")
                    print(f"  Error: {error_msg}")
                    print()
        
        # Print final status
        total_failed = sum(len(self.state[phase]['failed_files']) for phase in phases)
        if total_failed == 0:
            print("\nAll files processed successfully!")
        else:
            print(f"\nProcessing completed with {total_failed} failures.")

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

    def get_phase_instance(self, phase: str) -> Phase:
        """Get the phase instance for a given phase name.
        
        Args:
            phase: Name of the phase to get
            
        Returns:
            Phase instance
            
        Raises:
            ValueError: If phase name is invalid
        """
        if phase not in self.phases:
            raise ValueError(f"Unknown phase: {phase}")
        return self.phases[phase]

    def get_phases(self) -> List[str]:
        """Get list of available phases in order.
        
        Returns:
            List of phase names in execution order
        """
        return ["parse", "split", "finalize"]

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