"""Disassembly phase for Nova document processor."""

import logging
from pathlib import Path
from typing import Optional
import json

from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.store.manager import MetadataStore
from nova.context_processor.handlers.factory import HandlerFactory
from nova.context_processor.phases.base import Phase

logger = logging.getLogger(__name__)


class DisassemblyPhase(Phase):
    """Disassembly phase for document processing."""

    def __init__(self, config: NovaConfig, metadata_store: MetadataStore):
        """Initialize phase.

        Args:
            config: Nova configuration
            metadata_store: Metadata store instance
        """
        super().__init__(config, metadata_store)
        self.name = "disassembly"
        self.version = "1.0.0"
        self.handler_factory = HandlerFactory(config)

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a file in the disassembly phase.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Get handler for file
            handler = self.handler_factory.get_handler(file_path)
            if not handler:
                logger.warning(f"No handler found for {file_path}")
                return None

            # Create output directory structure
            file_output_dir = output_dir / file_path.stem
            if not file_output_dir.exists():
                file_output_dir.mkdir(parents=True, exist_ok=True)
                # Create attachments directory
                attachments_dir = file_output_dir / "attachments"
                attachments_dir.mkdir(exist_ok=True)

            # Disassemble file
            metadata = await handler.disassemble_file(file_path)
            if metadata:
                # Update base metadata
                self._update_base_metadata(file_path, metadata)

                # Create content file
                content_file = file_output_dir / "content.md"
                try:
                    with open(content_file, "w", encoding="utf-8") as f:
                        f.write(metadata.content or "")
                    metadata.output_files.add(str(content_file))
                except Exception as e:
                    logger.error(f"Failed to write content file {content_file}: {e}")
                    return None

                # Create metadata file
                metadata_file = file_output_dir / "metadata.json"
                try:
                    with open(metadata_file, "w", encoding="utf-8") as f:
                        json.dump(metadata.to_dict(), f, indent=2)
                    metadata.output_files.add(str(metadata_file))
                except Exception as e:
                    logger.error(f"Failed to write metadata file {metadata_file}: {e}")
                    return None

                return metadata

            return None

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
            logger.info(f"\nDisassembled documents")
            logger.info(f"Output directory: {output_dir}")

        except Exception as e:
            logger.error(f"Finalization failed: {str(e)}")
            raise

    async def process(self) -> bool:
        """Process files in phase.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get input files
            input_files = self._get_files(self.config.input_dir)
            if not input_files:
                logger.warning("No files found in input directory")
                return True

            # Process each file
            for file_path in input_files:
                try:
                    # Check if file should be processed
                    if not self.config.should_process_file(file_path):
                        logger.debug(f"Skipping {file_path}")
                        self.skipped_files.add(file_path)
                        continue

                    # Get metadata for file
                    metadata = self.metadata_store.get_metadata(file_path)
                    if not metadata:
                        logger.warning(f"No metadata found for {file_path}")
                        self.skipped_files.add(file_path)
                        continue

                    # TODO: Implement disassembly logic
                    # For now, just mark as processed
                    self.processed_files.add(file_path)

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    self.failed_files.add(file_path)

            return True

        except Exception as e:
            logger.error(f"Disassembly phase failed: {e}")
            return False 