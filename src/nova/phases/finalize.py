"""Finalize phase implementation."""

# Standard library
import logging
import shutil
from pathlib import Path
from typing import Optional

# External dependencies
from rich.console import Console
from rich.table import Table

# Internal imports
from ..core.metadata import FileMetadata
from ..phases.base import Phase
from ..validation.pipeline_validator import PipelineValidator

logger = logging.getLogger(__name__)


class FinalizePhase(Phase):
    """Finalize phase that processes split files and moves them to output directory."""

    def __init__(self, config, pipeline):
        """Initialize finalize phase.

        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        super().__init__("finalize", config, pipeline)
        self.validator = PipelineValidator(pipeline)

    async def process_impl(
        self, file_path: Path, output_dir: Path, metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file in the finalize phase.

        Args:
            file_path: Path to file to process
            output_dir: Directory to write output to (this will be the finalize phase dir)
            metadata: Optional metadata from previous phase

        Returns:
            FileMetadata if successful, None if failed
        """
        try:
            logger.info(f"Processing file in finalize phase: {file_path}")
            logger.info(f"Output directory is: {output_dir}")

            # Get relative path from split directory
            split_dir = self.pipeline.config.processing_dir / "phases" / "split"
            try:
                rel_path = file_path.relative_to(split_dir)
                logger.info(f"Got relative path: {rel_path}")
            except ValueError:
                # If not under split_dir, use just the filename
                rel_path = Path(file_path.name)
                logger.info(f"Using filename as relative path: {rel_path}")

            # Create output path in finalize directory using provided output_dir
            output_path = output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file to finalize directory
            shutil.copy2(file_path, output_path)
            logger.info(f"Copied {file_path} to {output_path}")

            # Create or update metadata
            if metadata is None:
                metadata = FileMetadata.from_file(
                    file_path=file_path, handler_name="finalize", handler_version="1.0"
                )
            metadata.processed = True
            metadata.add_output_file(output_path)

            # Save metadata file
            metadata_path = output_dir / f"{file_path.stem}.metadata.json"
            metadata.save(metadata_path)
            logger.info(f"Saved metadata to {metadata_path}")

            # Update pipeline state
            self.pipeline.state[self.name]["successful_files"].add(file_path)

            return metadata

        except Exception as e:
            logger.error(f"Failed to finalize {file_path}: {str(e)}")
            if metadata:
                metadata.add_error("finalize", str(e))
                metadata.processed = False

            # Update pipeline state
            self.pipeline.state[self.name]["failed_files"].add(file_path)

            return None

    def finalize(self) -> None:
        """Run pipeline validation and move files to output directory."""
        try:
            # Run validation
            validation_passed = self.validator.validate()
            if not validation_passed:
                logger.error("Pipeline validation failed. Aborting finalization.")
                self.pipeline.state[self.name]["failed_files"].add("validation")
                return

            # Move files from finalize directory to output directory
            finalize_dir = self.pipeline.config.processing_dir / "phases" / "finalize"
            if finalize_dir.exists():
                # Walk through all files in finalize directory
                for file_path in finalize_dir.rglob("*"):
                    if file_path.is_file():
                        # Get relative path from finalize dir
                        rel_path = file_path.relative_to(finalize_dir)
                        # Create output path
                        output_path = self.config.output_dir / rel_path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        # Copy file to output
                        shutil.copy2(file_path, output_path)
                        logger.info(f"Moved {file_path} to {output_path}")
                        self.pipeline.state[self.name]["successful_files"].add(
                            output_path
                        )

            # Update stats
            self.pipeline.state[self.name].update(
                {
                    "total_files": len(
                        self.pipeline.state[self.name]["successful_files"]
                    ),
                    "failed_files": len(self.pipeline.state[self.name]["failed_files"]),
                    "completed": True,
                    "success": validation_passed,
                }
            )

        except Exception as e:
            logger.error(f"Error in finalize phase: {str(e)}")
            self.pipeline.state[self.name]["failed_files"].add("finalize")
            self.pipeline.state[self.name].update({"completed": True, "success": False})
            raise

    async def process_files(self) -> None:
        """Process all files from the split phase."""
        split_dir = self.pipeline.config.processing_dir / "phases" / "split"
        if not split_dir.exists():
            logger.warning("Split phase directory does not exist")
            return

        # Get all files from split phase
        for file_path in split_dir.rglob("*"):
            if file_path.is_file():
                output_dir = self.pipeline.get_phase_output_dir("finalize")
                await self.process_file(file_path, output_dir)
