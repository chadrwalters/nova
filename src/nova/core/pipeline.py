"""Nova document processing pipeline."""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Set
import shutil

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
    ) -> DocumentMetadata:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            phases: List of phases to run.
            
        Returns:
            Document metadata.
        """
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
        processing_dir = self.config.processing_dir
        phases_dir = Path(processing_dir) / "phases"
        logger.debug(f"Checking if {file_path} needs reprocessing in {processing_dir}")

        # If processing directory doesn't exist yet, we need to process everything
        if not Path(processing_dir).exists():
            logger.debug("Processing directory doesn't exist yet - needs reprocessing")
            return True

        # If phases directory doesn't exist yet, we need to process everything
        if not phases_dir.exists():
            logger.debug("Phases directory doesn't exist yet - needs reprocessing")
            return True

        # Check if any phase directories are missing
        for phase in phases:
            phase_dir = phases_dir / phase
            if not phase_dir.exists():
                logger.debug(f"Phase directory {phase} doesn't exist yet - needs reprocessing")
                return True

        # If the user's input file or directory isn't valid, assume we need reprocessing
        if not file_path.exists():
            logger.debug(f"Input file {file_path} doesn't exist - needs reprocessing")
            return True

        # Get relative path from input directory
        input_dir = Path(self.config.input_dir)
        try:
            rel_path = file_path.relative_to(input_dir)
        except ValueError:
            logger.error(f"File {file_path} is not under input directory {input_dir}")
            return True

        # Check per-phase output
        for phase in phases:
            phase_dir = phases_dir / phase
            
            # For parse phase, check for .parsed extension
            if phase == "parse":
                # Get the stem and suffix of the relative path
                stem = rel_path.stem
                suffix = rel_path.suffix
                # Look for .parsed file
                output_path = phase_dir / f"{stem}.parsed{suffix}"
                logger.debug(f"Checking parse output: {output_path}")
                
                # If .parsed file doesn't exist => must reprocess
                if not output_path.exists():
                    logger.debug(f"Missing parsed output file for {phase}, reprocessing required")
                    return True
                
                # If output is older => must reprocess
                try:
                    input_mtime = file_path.stat().st_mtime
                    output_mtime = output_path.stat().st_mtime
                    if output_mtime < input_mtime:
                        logger.debug(
                            f"Output file {output_path} is older than input {file_path}"
                        )
                        return True
                except OSError as e:
                    logger.error(f"Error checking file times: {str(e)}")
                    return True
            else:
                # For other phases, use normal path
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
                    if output_mtime < input_mtime:
                        logger.debug(
                            f"Output file {output_path} is older than input {file_path}"
                        )
                        return True
                except OSError as e:
                    logger.error(f"Error checking file times: {str(e)}")
                    return True

        # If all phases have up-to-date outputs, we do NOT need reprocessing
        logger.debug(f"All outputs for {file_path} are up to date")
        return False
    
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
                        failed += 1
                        # Add failure details
                        error_msg = metadata.errors[-1]["message"] if metadata.errors else metadata.error
                        failures.append((file_path, error_msg))
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