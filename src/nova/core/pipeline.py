"""Nova pipeline implementation."""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from nova.config.manager import ConfigManager
from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from nova.phases.parse import ParsePhase
from nova.phases.split import SplitPhase
from nova.phases.finalize import FinalizePhase
from nova.core.logging import print_summary

logger = logging.getLogger(__name__)

class NovaPipeline:
    """Pipeline for processing files."""
    
    def __init__(self, config: ConfigManager):
        """Initialize pipeline.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize empty state
        self.state = {}
        
        # Initialize phases
        self.phases = {
            "parse": ParsePhase(self),
            "split": SplitPhase(self),
            "finalize": FinalizePhase(self)
        }
        
        # Reset state after phases are initialized
        self.reset_state()
        
    def reset_state(self) -> None:
        """Reset pipeline state."""
        # Initialize standard state for parse phase
        self.state = {
            "parse": {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set()
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
        
    async def process_directory(self, directory: Path, phases: List[str] = None) -> None:
        """Process all files in a directory.
        
        Args:
            directory: Directory to process
            phases: Optional list of phases to run. If None, run all phases.
        """
        # Reset state for this run
        self.reset_state()
        
        # Get list of phases to run
        if phases is None:
            phases = list(self.phases.keys())
        elif "finalize" not in phases:
            # Always append finalize phase if not included
            phases.append("finalize")
            
        # Process each phase
        for phase in phases:
            phase_start_time = time.time()
            logger.info(f"Running {phase} phase...")
            
            # Get phase instance
            phase_instance = self.phases[phase]
            
            # Special handling for finalize phase
            if phase == "finalize":
                # Check if previous phases succeeded
                if phase_instance.check_pipeline_success():
                    # Get files from split phase to copy
                    split_dir = self.config.processing_dir / "phases" / "split"
                    files = list(split_dir.rglob("*"))
                    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
                    
                    # Create output directory for finalize phase (temporary, for tracking)
                    output_dir = self.config.processing_dir / "phases" / "finalize"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Process each file (copy to output)
                    for file_path in files:
                        metadata = await phase_instance.process_file(file_path, output_dir)
                        if metadata is None:
                            self.state[phase]['failed_files'].add(file_path)
                        else:
                            self.state[phase]['successful_files'].add(file_path)
                else:
                    logger.warning("Skipping file copy in finalize phase due to previous phase failures")
                    
                # Print final summary
                phase_instance.print_final_summary()
                continue
            
            # For other phases, get files to process normally
            if phase == "parse":
                # For parse phase, get all files in input directory
                files = list(directory.rglob("*"))
                files = [f for f in files if f.is_file() and not f.name.startswith(".")]
            else:
                # For other phases, get files from previous phase
                prev_phase = phases[phases.index(phase) - 1]
                prev_phase_dir = self.config.processing_dir / "phases" / prev_phase
                files = list(prev_phase_dir.rglob("*"))
                files = [f for f in files if f.is_file() and not f.name.startswith(".")]
            
            # Create output directory
            output_dir = self.config.processing_dir / "phases" / phase
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process each file
            for i, file_path in enumerate(files, 1):
                logger.info(f"Processing file {i}/{len(files)}: {file_path.name}")
                
                # Check if file needs reprocessing
                needs_reprocess = await self.needs_reprocessing(file_path, phase)
                if not needs_reprocess:
                    self.state[phase]['unchanged_files'].add(file_path)
                    continue
                    
                # Process file
                metadata = await phase_instance.process_file(file_path, output_dir)
                
                # Update state based on metadata
                if metadata is None:
                    self.state[phase]['failed_files'].add(file_path)
                elif metadata.unchanged:
                    self.state[phase]['unchanged_files'].add(file_path)
                else:
                    self.state[phase]['successful_files'].add(file_path)
                    if metadata.reprocessed:
                        self.state[phase]['reprocessed_files'].add(file_path)
            
            # Call finalize after all files have been processed
            if hasattr(phase_instance, 'finalize'):
                phase_instance.finalize()
            
            # Print phase summary
            phase_duration = time.time() - phase_start_time
            print(f"\n{phase.upper()} Phase Summary")
            
            # Use different summary format for split phase
            if phase == "split":
                print("\n   Processing Summary")
                print("┏━━━━━━━━━━━━━┳━━━━━━━━┓")
                print("┃ Metric      ┃  Value ┃")
                print("┡━━━━━━━━━━━━━╇━━━━━━━━┩")
                print(f"│ Summaries   │ {self.state[phase]['summary_sections']:>6d} │")
                print(f"│ Raw Notes   │ {self.state[phase]['raw_notes_sections']:>6d} │")
                print(f"│ Attachments │ {self.state[phase]['attachments']:>6d} │")
                print(f"│ Failed      │ {len(self.state[phase]['failed_files']):>6d} │")
                print(f"│ Duration    │ {phase_duration:>6.2f}s │")
                print("└─────────────┴────────┘")
            else:
                # Enhanced summary with reprocessing info
                total_files = len(files)
                successful = len(self.state[phase]['successful_files'])
                failed = len(self.state[phase]['failed_files'])
                skipped = len(self.state[phase]['skipped_files'])
                unchanged = len(self.state[phase]['unchanged_files'])
                reprocessed = len(self.state[phase]['reprocessed_files'])
                
                # For parse phase, count unchanged files as processed
                if phase == "parse":
                    processed = successful + unchanged
                else:
                    processed = successful
                
                print("\n   Processing Summary")
                print("┏━━━━━━━━━━━━━┳━━━━━━━━┓")
                print("┃ Metric      ┃  Value ┃")
                print("┡━━━━━━━━━━━━━╇━━━━━━━━┩")
                print(f"│ Total Files │ {total_files:>6d} │")
                print(f"│ Processed   │ {processed:>6d} │")
                print(f"│ Failed      │ {failed:>6d} │")
                print(f"│ Skipped     │ {skipped:>6d} │")
                print(f"│ Unchanged   │ {unchanged:>6d} │")
                print(f"│ Reprocessed │ {reprocessed:>6d} │")
                print(f"│ Duration    │ {phase_duration:>6.2f}s │")
                print("└─────────────┴────────┘")
                
                # Print list of unchanged and reprocessed files if any
                if unchanged > 0:
                    print("\nUnchanged files:")
                    for f in sorted(self.state[phase]['unchanged_files']):
                        print(f"  • {f.name}")
                        
                if reprocessed > 0:
                    print("\nReprocessed files:")
                    for f in sorted(self.state[phase]['reprocessed_files']):
                        print(f"  • {f.name}")

    async def needs_reprocessing(self, file_path: Path, phase: str) -> bool:
        """Return True if any phase output is missing or older than the input file;
        otherwise False.
        """
        # Skip .DS_Store files
        if file_path.name == ".DS_Store":
            return False
            
        processing_dir = self.config.processing_dir
        phases_dir = Path(processing_dir) / "phases"
        logger.debug(f"Checking if {file_path} needs reprocessing in {processing_dir}")

        # For parse phase, check against input directory
        if phase == "parse":
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
            except OSError as e:
                logger.error(f"Error checking file times: {str(e)}")
                return True
                
        else:
            # For split phase, check if output exists and is newer than input
            output_path = phases_dir / phase / file_path.name
            
            # If output doesn't exist => must reprocess
            if not output_path.exists():
                logger.info(f"No previous output found for {file_path.name} in {phase} phase - will process")
                return True
            
            # If output is older => must reprocess
            try:
                input_mtime = file_path.stat().st_mtime
                output_mtime = output_path.stat().st_mtime
                logger.debug(f"Comparing timestamps for {file_path.name}")
                
                # Get formatted timestamps for logging
                input_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(input_mtime))
                output_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(output_time))
                
                if output_mtime < input_mtime:
                    logger.info(f"File {file_path.name} modified ({input_time}) after last {phase} processing ({output_time}) - will reprocess")
                    return True
                else:
                    logger.info(f"File {file_path.name} unchanged since last {phase} processing ({output_time}) - skipping")
            except OSError as e:
                logger.error(f"Error checking file times: {str(e)}")
                return True

        # Check if input file has been modified
        try:
            # Get current file content
            with open(file_path, 'rb') as f:
                current_content = f.read()
            
            # Get previous file content from cache
            cache_dir = Path(self.config.cache_dir) / "content"
            cache_file = cache_dir / file_path.name
            
            # If cache file doesn't exist => must reprocess
            if not cache_file.exists():
                # Create cache directory and save current content
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, 'wb') as f:
                    f.write(current_content)
                logger.info(f"No content cache found for {file_path.name} - will process")
                return True
            
            # Compare content
            with open(cache_file, 'rb') as f:
                cached_content = f.read()
            
            if current_content != cached_content:
                # Update cache with new content
                with open(cache_file, 'wb') as f:
                    f.write(current_content)
                logger.info(f"Content changed for {file_path.name} - will reprocess")
                return True
            else:
                logger.debug(f"Content unchanged for {file_path.name}")
                
        except Exception as e:
            logger.error(f"Error checking file content: {str(e)}")
            return True

        # If we get here, we don't need to reprocess
        return False

    def get_phase_output_dir(self, phase: str) -> Path:
        """Get the output directory for a phase."""
        return self.config.processing_dir / "phases" / phase

    def get_phase(self, phase: str) -> Union[ParsePhase, SplitPhase]:
        """Get the phase instance for a given phase name."""
        if phase == "parse":
            handler_registry = HandlerRegistry(self.config)
            return ParsePhase(self.config, handler_registry)
        elif phase == "split":
            return SplitPhase(self.config)
        else:
            raise ValueError(f"Unknown phase: {phase}")

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