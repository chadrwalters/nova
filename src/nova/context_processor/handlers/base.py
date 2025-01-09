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
    """Base class for all handlers."""

    def __init__(self, config: ConfigManager):
        """Initialize handler.

        Args:
            config: Configuration manager
        """
        self.config = config
        self.temp_dir = Path(config.temp_dir)
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.supported_extensions = set()

    async def parse_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Parse a file.

        Args:
            file_path: Path to file to parse

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata
            metadata = BaseMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=self._calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
            )

            # Process file
            if await self._process_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Process a file.

        Args:
            file_path: Path to file to process
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Create output file path preserving original extension
            output_file = self.temp_dir / file_path.name

            # Copy file to temp directory
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())

            metadata.output_files.add(str(output_file))
            return True

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash.

        Args:
            file_path: Path to file

        Returns:
            str: File hash
        """
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    async def disassemble_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Disassemble a file.

        Args:
            file_path: Path to file to disassemble

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata
            metadata = BaseMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=self._calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
            )

            # Process file
            if await self._disassemble_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to disassemble file {file_path}: {str(e)}")
            return None

    async def _disassemble_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Disassemble a file.

        Args:
            file_path: Path to file to disassemble
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # Create output file path preserving original extension
            output_file = self.temp_dir / file_path.name

            # Copy file to temp directory
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())

            metadata.output_files.add(str(output_file))
            return True

        except Exception as e:
            logger.error(f"Failed to disassemble file {file_path}: {str(e)}")
            return False

    async def split_file(self, file_path: Path, metadata: Optional[BaseMetadata] = None) -> Optional[BaseMetadata]:
        """Split a file.

        Args:
            file_path: Path to file to split
            metadata: Optional metadata to update

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata if not provided
            if not metadata:
                metadata = BaseMetadata(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_type=file_path.suffix.lstrip('.'),
                    file_size=file_path.stat().st_size,
                    file_hash=calculate_file_hash(file_path),
                    created_at=file_path.stat().st_ctime,
                    modified_at=file_path.stat().st_mtime,
                )

            # Process file
            if await self._split_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to split file {file_path}: {str(e)}")
            return None

    async def _split_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Split a file.

        Args:
            file_path: Path to file to split
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # Create output file path preserving original extension
            output_file = self.temp_dir / file_path.name

            # Copy file to temp directory
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())

            metadata.output_files.add(str(output_file))
            return True

        except Exception as e:
            logger.error(f"Failed to split file {file_path}: {str(e)}")
            return False
