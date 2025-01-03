"""Finalize phase implementation."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from nova.validation.pipeline_validator import PipelineValidator

logger = logging.getLogger(__name__)

class FinalizePhase(Phase):
    """Finalize phase that copies processed files to output directory."""
    
    def __init__(self, config, pipeline):
        """Initialize finalize phase.
        
        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        super().__init__("finalize", config, pipeline)
        self.validator = PipelineValidator(config)
        
    async def process_file(self, file_path: Path, output_dir: Path) -> Optional[FileMetadata]:
        """Process a single file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output to
            
        Returns:
            FileMetadata if successful, None if failed
        """
        try:
            # Copy file to output directory
            output_file = self.config.output_dir / file_path.name
            shutil.copy2(file_path, output_file)
            logger.debug(f"Copied {file_path} to {output_file}")
            
            # Create metadata
            metadata = FileMetadata(file_path=file_path)
            metadata.processed = True
            metadata.add_output_file(output_file)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to finalize {file_path}: {str(e)}")
            return None
            
    def finalize(self) -> None:
        """Run pipeline validation and cleanup."""
        logger.info("Running pipeline validation...")
        
        # Run validation
        validation_passed = self.validator.validate()
        if not validation_passed:
            logger.error("Pipeline validation failed. Aborting finalization.")
            return
            
        # Copy attachments
        logger.info("Copying attachments...")
        split_dir = self.config.processing_dir / "phases" / "split"
        if split_dir.exists():
            for file_name in ["Summary.md", "Raw Notes.md", "Attachments.md"]:
                src = split_dir / file_name
                if src.exists():
                    dst = self.config.output_dir / file_name
                    shutil.copy2(src, dst)
                    logger.debug(f"Copied {src} to {dst}")
                    
        # Print summary
        logger.info("\n=== Finalize Phase Summary ===")
        
        # Report validation status
        if not validation_passed:
            logger.warning("Pipeline validation: FAILED")
        else:
            logger.info("Pipeline validation: PASSED")
            
        # Report attachments copying
        logger.info("Attachments copying: COMPLETED")

        # Report cleanup stats
        logger.info("\nCleanup Statistics:")
        logger.info(f"- Temporary files removed: 0")
        logger.info(f"- Directories removed: 0")
        
        logger.info("\nFinalize phase completed successfully!") 