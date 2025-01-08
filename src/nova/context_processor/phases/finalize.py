"""Finalize phase for processing documents."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.store.manager import MetadataStore
from nova.context_processor.handlers.factory import HandlerFactory
from nova.context_processor.phases.base import Phase

logger = logging.getLogger(__name__)


class FinalizePhase(Phase):
    """Phase for finalizing document processing."""

    def __init__(self, config: NovaConfig, metadata_store: MetadataStore):
        """Initialize finalize phase.

        Args:
            config: Nova configuration
            metadata_store: Metadata store instance
        """
        super().__init__(config, metadata_store)
        self.name = "finalize"
        self.version = "1.0.0"
        self.handler_factory = HandlerFactory(config)

    async def process(self) -> bool:
        """Process files in finalize phase.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get input files
            input_files = self._get_files(self.config.input_dir)
            if not input_files:
                logger.warning("No files found in input directory")
                return True

            # Get output directory
            output_dir = self.config.base_dir / "_NovaProcessing" / "phases" / self.name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process each file
            for file_path in input_files:
                try:
                    # Check if file should be processed
                    if not self.config.should_process_file(file_path):
                        logger.debug(f"Skipping {file_path}")
                        self.skipped_files.add(file_path)
                        continue

                    # Get metadata from previous phase
                    metadata = self._get_metadata(file_path)
                    
                    # Process file
                    metadata = await self.process_file(file_path, output_dir, metadata)
                    if metadata:
                        # Save metadata
                        if self._save_metadata(file_path, metadata):
                            self.processed_files.add(file_path)
                            continue

                    # If we get here, processing failed
                    logger.error(f"Failed to process {file_path}")
                    self.failed_files.add(file_path)

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    self.failed_files.add(file_path)

            # Run finalization steps
            self.finalize()
            return True

        except Exception as e:
            logger.error(f"Finalize phase failed: {e}")
            return False

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a file in the finalize phase.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Skip non-parsed markdown files
            if not str(file_path).endswith(".parsed.md"):
                return metadata

            # Create metadata if not provided
            if not metadata:
                metadata = MetadataFactory.create(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version=self.version,
                )

            # Update base metadata
            self._update_base_metadata(file_path, metadata)

            # Create output directory structure
            base_name = file_path.stem.replace(".parsed", "")
            final_dir = output_dir / base_name
            final_dir.mkdir(parents=True, exist_ok=True)

            # Copy all output files from previous phases
            changes = []
            for output_file in metadata.output_files:
                output_path = Path(output_file)
                if output_path.exists():
                    dest_path = final_dir / output_path.name
                    shutil.copy2(output_path, dest_path)
                    changes.append(f"Copied {output_path.name} to final directory")

            # Update metadata
            metadata.metadata["final_dir"] = str(final_dir)
            metadata.processed = True
            metadata.add_version(
                phase=self.name,
                changes=changes,
            )

            return metadata

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            if metadata:
                metadata.add_error(self.__class__.__name__, str(e))
            return None

    def finalize(self) -> None:
        """Run finalization steps."""
        try:
            # Get output directory
            output_dir = self.config.base_dir / "_NovaProcessing" / "phases" / self.name

            # Log summary
            logger.info(f"\nFinalized documents")
            logger.info(f"Output directory: {output_dir}")

        except Exception as e:
            logger.error(f"Finalization failed: {str(e)}")
            raise
