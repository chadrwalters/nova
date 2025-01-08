"""Base phase class for Nova document processor."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set

from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.store.manager import MetadataStore

logger = logging.getLogger(__name__)


class Phase(ABC):
    """Base class for processing phases."""

    def __init__(self, config: NovaConfig, metadata_store: MetadataStore):
        """Initialize phase.

        Args:
            config: Nova configuration
            metadata_store: Metadata store instance
        """
        self.config = config
        self.metadata_store = metadata_store
        self.processed_files: Set[Path] = set()
        self.failed_files: Set[Path] = set()
        self.skipped_files: Set[Path] = set()

    @abstractmethod
    def process(self) -> bool:
        """Process files in phase.

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a single file.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        pass

    @abstractmethod
    def finalize(self) -> None:
        """Run finalization steps."""
        pass

    def _update_base_metadata(self, file_path: Path, metadata: BaseMetadata) -> None:
        """Update base metadata fields.

        Args:
            file_path: Path to file
            metadata: Metadata instance to update
        """
        try:
            # Update file info
            metadata.file_path = str(file_path)
            metadata.file_name = file_path.name
            metadata.file_size = file_path.stat().st_size
            metadata.file_type = file_path.suffix.lower()

            # Add version info
            metadata.add_version(
                phase=self.__class__.__name__,
                changes=[f"Updated base metadata for {file_path.name}"],
            )

        except Exception as e:
            logger.error(f"Failed to update base metadata for {file_path}: {str(e)}")
            metadata.add_error(self.__class__.__name__, str(e))

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics.

        Returns:
            Dict[str, int]: Statistics dictionary
        """
        return {
            "processed": len(self.processed_files),
            "failed": len(self.failed_files),
            "skipped": len(self.skipped_files),
        }

    def _save_metadata(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Save metadata for file.

        Args:
            file_path: Path to file
            metadata: Metadata instance

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.metadata_store.save(file_path, metadata)
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata for {file_path}: {e}")
            return False

    def _get_metadata(self, file_path: Path) -> Optional[BaseMetadata]:
        """Get metadata for file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata instance if found, None otherwise
        """
        try:
            return self.metadata_store.get(file_path)
        except Exception as e:
            logger.error(f"Failed to get metadata for {file_path}: {e}")
            return None

    def _get_files(self, directory: Path, pattern: str = "*") -> List[Path]:
        """Get files in directory matching pattern.

        Args:
            directory: Directory to search
            pattern: Glob pattern

        Returns:
            List[Path]: List of matching files
        """
        try:
            return sorted(directory.glob(pattern))
        except Exception as e:
            logger.error(f"Failed to get files from {directory}: {e}")
            return []
