"""Disassembly phase for document processing."""

import logging
from pathlib import Path
from typing import Optional

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

            # Disassemble file
            metadata = await handler.disassemble_file(file_path)
            if metadata:
                # Update base metadata
                self._update_base_metadata(file_path, metadata)
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
        """Run the disassembly phase."""
        try:
            # Get all files in the disassembly phase directory
            disassembly_dir = self.config.base_dir / "_NovaProcessing" / "phases" / self.name
            files = [f for f in disassembly_dir.iterdir() if f.is_file()]

            # Process each file
            for file in files:
                await self.process_file(file, disassembly_dir)

            return True

        except Exception as e:
            logger.error(f"Failed to process phase: {str(e)}")
            return False
