"""Nova document processing pipeline."""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Set
import shutil
from datetime import datetime
import json

from nova.core.logging import create_progress_bar, print_summary
from nova.core.progress import FileProgress, PhaseProgress, ProcessingStatus, ProgressTracker
from nova.models.document import DocumentMetadata
from nova.config.manager import ConfigManager

logger = logging.getLogger("nova")


class NovaPipeline:
    """Nova document processing pipeline."""
    
    def __init__(self):
        """Initialize pipeline."""
        self.progress = ProgressTracker()
        self.progress_bar = create_progress_bar()
        self.unchanged_files = 0
        self.reprocessed_files = 0
        self.config = ConfigManager()
    
    async def process_file(
        self,
        file_path: Path,
        phases: List[str],
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            phases: List of phases to run.
            
        Returns:
            Document metadata.
        """
        # Skip .DS_Store files completely
        if file_path.name == ".DS_Store":
            logger.debug(f"Skipping ignored file: {file_path}")
            return None
            
        # Start tracking progress for this file
        await self.progress.start_file(file_path)
        
        # Get relative path from input directory
        input_dir = Path(self.config.input_dir)
        try:
            rel_path = file_path.relative_to(input_dir)
        except ValueError:
            logger.error(f"File {file_path} is not under input directory {input_dir}")
            return DocumentMetadata.from_file(
                file_path=file_path,
                handler_name="nova",
                handler_version="0.1.0",
            )
        
        # Initialize metadata
        metadata = await self.get_existing_metadata(file_path)
        
        # Create phase directories
        processing_dir = Path(self.config.processing_dir)
        logger.debug(f"Creating processing directory: {processing_dir}")
        processing_dir.mkdir(parents=True, exist_ok=True)
        
        phases_dir = processing_dir / "phases"
        logger.debug(f"Creating phases directory: {phases_dir}")
        phases_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Creating phase directories for phases: {phases}")
        for phase in phases:
            phase_dir = phases_dir / phase
            logger.debug(f"Creating phase directory: {phase_dir}")
            phase_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created phase directory: {phase_dir}")
        
        # Check if we need reprocessing
        needs_reprocessing = await self.needs_reprocessing(file_path, phases)
        logger.debug(f"Needs reprocessing: {needs_reprocessing}")
        
        if needs_reprocessing:
            self.reprocessed_files += 1
            logger.info(f"Reprocessing {file_path} (changed)")

            # Process each phase
            for phase in phases:
                logger.info(f"[{phase}] Starting {phase} phase")
                try:
                    await self.progress.start_phase(phase, file_path)
                    
                    # Prepare formal output path
                    phase_dir = phases_dir / phase
                    # Preserve the relative directory structure
                    output_path = phase_dir / rel_path
                    # Create all parent directories
                    logger.debug(f"Creating parent directories for: {output_path}")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Output path: {output_path}")
                    
                    # Import and use the appropriate phase module
                    if phase == "parse":
                        from nova.phases.parse import ParsePhase
                        from nova.handlers.registry import HandlerRegistry
                        handler_registry = HandlerRegistry(self.config)
                        phase_module = ParsePhase(self.config, handler_registry)
                        
                        # Process the file - don't copy it first
                        metadata = await phase_module.process(file_path, output_path, metadata)
                        
                    elif phase == "split":
                        from nova.phases.split import SplitPhase
                        phase_module = SplitPhase(self.config)
                        
                        # First, copy the original file to the output path
                        logger.debug(f"Copying {file_path} to {output_path}")
                        shutil.copy2(file_path, output_path)
                        
                        # Process the file
                        metadata = await phase_module.process(file_path, output_path, metadata)
                    else:
                        logger.error(f"Unknown phase: {phase}")
                        metadata.add_error(phase, f"Unknown phase: {phase}")
                        await self.progress.fail_phase(phase, file_path)
                        break
                    
                    # Complete phase
                    await self.progress.complete_phase(phase, file_path)
                    logger.info(
                        f"[{phase}] Completed {phase} phase",
                        extra={"duration": self.progress.phases[phase].duration},
                    )
                    
                except Exception as e:
                    logger.error(f"Error in {phase} phase: {str(e)}")
                    metadata.add_error(phase, str(e))
                    await self.progress.fail_phase(phase, file_path)
                    break
        else:
            self.unchanged_files += 1
            logger.info(f"Using existing processed output for {file_path} (unchanged)")
            
            # Copy existing outputs to phase directories
            for phase in phases:
                phase_dir = phases_dir / phase
                if phase == "parse":
                    # Skip copying for parse phase - handlers should create markdown files
                    continue
                else:
                    # For other phases, use normal path
                    output_path = phase_dir / rel_path
                    logger.debug(f"Creating parent directories for: {output_path}")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    if not output_path.exists():
                        logger.debug(f"Copying {file_path} to {output_path}")
                        shutil.copy2(file_path, output_path)
        
        # Complete file processing
        duration = await self.progress.complete_file(file_path)
        logger.info(f"Completed processing file: {file_path}", extra={"duration": duration})
        return metadata
    
    async def needs_reprocessing(self, file_path: Path, phases: List[str]) -> bool:
        """
        Return True if any phase output is missing or older than the input file;
        otherwise False.
        """
        # Skip .DS_Store files
        if file_path.name == ".DS_Store":
            return False
            
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
            logger.debug(f"Input file {file_path} doesn't exist - needs reprocessing")
            return True

        # Check if output exists for each phase
        for phase in phases:
            phase_dir = phases_dir / phase
            
            # For parse phase, look for .parsed.md file in the same relative directory
            if phase == "parse":
                # Preserve directory structure
                relative_output_dir = phase_dir / rel_path.parent
                output_path = relative_output_dir / f"{rel_path.stem}.parsed.md"
                logger.debug(f"Checking parse output: {output_path}")
                
                # If .parsed.md file doesn't exist => must reprocess
                if not output_path.exists():
                    logger.debug(f"Missing parsed output file for {phase}, reprocessing required")
                    return True
                
                # Check if input is newer than output
                try:
                    input_mtime = file_path.stat().st_mtime
                    output_mtime = output_path.stat().st_mtime
                    logger.debug(f"Comparing timestamps for {file_path.name}")
                    if output_mtime < input_mtime:
                        logger.debug(f"Output file {output_path} is older than input file {file_path}, reprocessing required")
                        return True
                except OSError as e:
                    logger.error(f"Error checking file times: {str(e)}")
                    return True
                    
            else:
                # For other phases, use normal path preserving directory structure
                output_path = phase_dir / rel_path
                logger.debug(f"Checking output: {output_path}")
                
                # If file doesn't exist for this phase => must reprocess
                if not output_path.exists():
                    logger.debug(f"Missing output file for {phase}, reprocessing required")
                    return True
                
                # If output is older => must reprocess
                try:
                    input_mtime = file_path.stat().st_mtime
                    output_mtime = output_path.stat().st_mtime
                    logger.debug(f"Comparing timestamps for {file_path.name}")
                    if output_mtime < input_mtime:
                        logger.debug(f"Output file {output_path} is older than input file {file_path}, reprocessing required")
                        return True
                except OSError as e:
                    logger.error(f"Error checking file times: {str(e)}")
                    return True

        # Check cache state
        cache_state_dir = Path(self.config.cache_dir) / "state"
        processing_history_path = cache_state_dir / "processing_history.json"
        
        if processing_history_path.exists():
            try:
                with open(processing_history_path, 'r') as f:
                    processing_history = json.loads(f.read())
                    
                # Check if file is in processing history
                file_history = processing_history.get(str(file_path))
                if file_history:
                    # Get the cached modification time
                    cached_mtime = file_history.get('modified_time')
                    current_mtime = file_path.stat().st_mtime
                    
                    # If file hasn't been modified since last processing, we can skip
                    if cached_mtime and current_mtime <= cached_mtime:
                        logger.debug(f"File {file_path} hasn't been modified since last processing")
                        return False
                    else:
                        logger.debug(f"File {file_path} has been modified since last processing")
                        return True
            except Exception as e:
                logger.error(f"Error reading processing history: {str(e)}")
                # If we can't read the cache, assume we need to reprocess
                return True

        # If we get here, we need to reprocess
        return True
    
    async def get_existing_metadata(self, file_path: Path) -> DocumentMetadata:
        """Get metadata from existing processed output.
        
        Args:
            file_path: Path to input file.
            
        Returns:
            Metadata from existing processed output.
        """
        # TODO: Load metadata from existing output file
        return DocumentMetadata.from_file(
            file_path=file_path,
            handler_name="nova",
            handler_version="0.1.0",
        )
    
    async def process_directory(
        self,
        input_dir: Path,
        phases: List[str],
    ) -> None:
        """Process all files in a directory.
        
        Args:
            input_dir: Directory containing files to process.
            phases: List of phases to run.
        """
        # Log input directory
        logger.info(f"Searching for files in: {input_dir}")
        
        # Get list of files to process
        files = [f for f in input_dir.rglob("*") if f.is_file() and f.name != ".DS_Store"]
        total_files = len(files)
        
        # Log found files
        logger.info(f"Found {total_files} files to process:")
        for file in files:
            logger.info(f"  - {file.name}")
        
        # Initialize progress tracking
        start_time = time.time()
        for phase in phases:
            await self.progress.add_phase(phase, total_files)
        
        # Create progress bar task
        task_id = self.progress_bar.add_task(
            "Processing files...",
            total=total_files,
        )
        
        # Process files
        successful = 0
        failed = 0
        skipped = 0
        failures = []
        
        with self.progress_bar:
            for i, file_path in enumerate(files, 1):
                # Log progress
                logger.info(f"Processing file {i}/{total_files}: {file_path.name}", extra={"progress": f"{i}/{total_files}"})
                
                try:
                    # Process file
                    metadata = await self.process_file(file_path, phases)
                    
                    # Update counters
                    if metadata is None:
                        # File was ignored or no handler available
                        skipped += 1
                    elif metadata.errors or metadata.error:
                        # Only count as failure if it's not an ignored file
                        if not any(err.get("message", "").startswith("No handler found") for err in metadata.errors):
                            failed += 1
                            # Add failure details
                            error_msg = metadata.errors[-1]["message"] if metadata.errors else metadata.error
                            failures.append((file_path, error_msg))
                        else:
                            skipped += 1
                    else:
                        successful += 1
                    
                except Exception as e:
                    # Log error and update counter
                    logger.error(f"Failed to process file: {file_path}\n{str(e)}")
                    failed += 1
                    failures.append((file_path, str(e)))
                
                # Update progress bar
                self.progress_bar.update(task_id, advance=1)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log completion
        logger.info(
            "Directory processing complete",
            extra={
                "duration": duration,
                "total_files": total_files,
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "unchanged": self.unchanged_files,
                "reprocessed": self.reprocessed_files,
            },
        )
        
        # Print summary table
        print_summary(
            total_files=total_files,
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration=duration,
            unchanged=self.unchanged_files,
            reprocessed=self.reprocessed_files,
            failures=failures
        ) 