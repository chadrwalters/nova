import logging
from pathlib import Path
from typing import Optional

from nova.context_processor.core.handlers.base import BaseHandler
from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.models.factory import MetadataFactory
from nova.context_processor.phases.base import Phase
from nova.context_processor.handlers.factory import HandlerFactory
from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.metadata.store.manager import MetadataStore

logger = logging.getLogger(__name__)

class ParsePhase(Phase):
    """Parse phase."""

    def __init__(self, config: NovaConfig, metadata_store: MetadataStore):
        """Initialize phase.

        Args:
            config: Nova configuration
            metadata_store: Metadata store instance
        """
        super().__init__(config, metadata_store)
        self.handler_factory = HandlerFactory(config)

    def process(self) -> bool:
        """Process files in phase.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            input_dir = Path(self.config.input_directory)
            output_dir = Path(self.config.get_phase_output_dir("parse"))
            output_dir.mkdir(parents=True, exist_ok=True)

            files = self._get_files(input_dir)
            for file_path in files:
                result = self.process_file(file_path, output_dir)
                if result:
                    self.processed_files.add(file_path)
                else:
                    self.failed_files.add(file_path)

            return len(self.failed_files) == 0

        except Exception as e:
            logger.error(f"Failed to process parse phase: {str(e)}")
            return False

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a file.

        Args:
            file_path: Path to file
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

            # Create metadata if not provided
            if not metadata:
                metadata = MetadataFactory.create_metadata(file_path)
                if not metadata:
                    logger.error(f"Failed to create metadata for {file_path}")
                    return None

            # Process file
            handler.parse_file(file_path)
            metadata.output_files.add(str(output_dir / file_path.name))

            # Save metadata
            self._save_metadata(file_path, metadata)

            return metadata

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            return None

    def finalize(self) -> None:
        """Run finalization steps."""
        logger.info("\nParsed documents")
        logger.info(f"Output directory: {self.config.get_phase_output_dir('parse')}") 