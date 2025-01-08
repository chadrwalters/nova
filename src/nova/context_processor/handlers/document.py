"""Document handler for Nova document processor."""

import logging
from pathlib import Path

from nova.context_processor.core.metadata.models.types import DocumentMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class DocumentHandler(BaseHandler):
    """Handler for document files."""

    def __init__(self, config):
        """Initialize handler.

        Args:
            config: Nova configuration
        """
        super().__init__(config)
        self.supported_extensions = {
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
        }

    async def _process_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Process a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Extract text content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Update metadata
            metadata.content = content
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to process document {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Parse a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Extract text content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Update metadata
            metadata.content = content
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to parse document {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Disassemble a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble document {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Split a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split document {file_path}: {e}")
            return False
