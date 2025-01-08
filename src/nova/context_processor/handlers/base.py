"""Base handler for document processing."""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Set

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.models.factory import MetadataFactory
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of file processing."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class ProcessingResult:
    """Result of file processing."""

    def __init__(
        self,
        file_path: Path,
        status: ProcessingStatus,
        metadata: Optional[BaseMetadata] = None,
        error: Optional[str] = None,
    ) -> None:
        """Initialize result.

        Args:
            file_path: Path to processed file
            status: Processing status
            metadata: Optional metadata
            error: Optional error message
        """
        self.file_path = file_path
        self.status = status
        self.metadata = metadata
        self.error = error

    def __str__(self) -> str:
        """String representation of result."""
        return f"ProcessingResult(file={self.file_path}, status={self.status})"


class BaseHandler:
    """Base handler for document processing."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.

        Args:
            config: Nova configuration
        """
        self.config = config
        self.name = self.__class__.__name__.lower().replace("handler", "")
        self.version = "1.0.0"
        self.supported_extensions: Set[str] = set()
        self.mime_types: Set[str] = set()

    async def process_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Process a file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None otherwise
        """
        try:
            # Calculate file hash
            file_hash = calculate_file_hash(file_path)
            if not file_hash:
                logger.error(f"Failed to calculate hash for {file_path}")
                return None

            # Create metadata
            metadata = MetadataFactory.create(
                file_path=file_path,
                handler_name=self.name,
                handler_version=self.version,
                file_type=file_path.suffix.lower(),
                file_hash=file_hash
            )

            # Process file
            if await self._process_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None

    async def parse_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Parse a file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None otherwise
        """
        try:
            # Calculate file hash
            file_hash = calculate_file_hash(file_path)
            if not file_hash:
                logger.error(f"Failed to calculate hash for {file_path}")
                return None

            # Create metadata
            metadata = MetadataFactory.create(
                file_path=file_path,
                handler_name=self.name,
                handler_version=self.version,
                file_type=file_path.suffix.lower(),
                file_hash=file_hash
            )

            # Parse file
            if await self._parse_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    async def disassemble_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Disassemble a file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None otherwise
        """
        try:
            # Calculate file hash
            file_hash = calculate_file_hash(file_path)
            if not file_hash:
                logger.error(f"Failed to calculate hash for {file_path}")
                return None

            # Create metadata
            metadata = MetadataFactory.create(
                file_path=file_path,
                handler_name=self.name,
                handler_version=self.version,
                file_type=file_path.suffix.lower(),
                file_hash=file_hash
            )

            # Disassemble file
            if await self._disassemble_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to disassemble {file_path}: {e}")
            return None

    async def split_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Split a file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None otherwise
        """
        try:
            # Calculate file hash
            file_hash = calculate_file_hash(file_path)
            if not file_hash:
                logger.error(f"Failed to calculate hash for {file_path}")
                return None

            # Create metadata
            metadata = MetadataFactory.create(
                file_path=file_path,
                handler_name=self.name,
                handler_version=self.version,
                file_type=file_path.suffix.lower(),
                file_hash=file_hash
            )

            # Split file
            if await self._split_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to split {file_path}: {e}")
            return None

    async def _process_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Process a file and update metadata.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        raise NotImplementedError("Subclasses must implement _process_file")

    async def _parse_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Parse a file and update metadata.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        raise NotImplementedError("Subclasses must implement _parse_file")

    async def _disassemble_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Disassemble a file and update metadata.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        raise NotImplementedError("Subclasses must implement _disassemble_file")

    async def _split_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Split a file and update metadata.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        raise NotImplementedError("Subclasses must implement _split_file")

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.

        Args:
            file_path: Path to file

        Returns:
            bool: Whether handler can process file
        """
        return file_path.suffix.lower() in self.supported_extensions
