"""Metadata store manager."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union

from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.store.search_index import MetadataIndex
from nova.context_processor.core.metadata.store.encoders import CustomJSONEncoder

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseMetadata)


class MetadataStore:
    """Manages storage and retrieval of document metadata."""

    def __init__(self, store_dir: Union[str, Path]) -> None:
        """Initialize metadata store.

        Args:
            store_dir: Directory to store metadata files
        """
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index = MetadataIndex(self.store_dir / "index.json")

    def save(self, metadata: BaseMetadata) -> bool:
        """Save metadata to store.

        Args:
            metadata: Metadata to save

        Returns:
            bool: Whether save was successful
        """
        try:
            # Convert metadata to JSON-serializable dict
            metadata_dict = metadata.model_dump()

            # Save to file
            metadata_path = self._get_metadata_path(metadata.file_path)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f, cls=CustomJSONEncoder, indent=2)

            # Update index
            self.index.add_metadata(metadata)
            
            return True

        except Exception as e:
            logger.error(f"Failed to save metadata for {metadata.file_path}: {e}")
            return False

    def load(self, file_path: Union[str, Path], metadata_class: Type[T] = BaseMetadata) -> Optional[T]:
        """Load metadata from store.

        Args:
            file_path: Path to original file
            metadata_class: Class to instantiate metadata as

        Returns:
            Optional[BaseMetadata]: Loaded metadata or None if not found
        """
        try:
            metadata_path = self._get_metadata_path(file_path)
            if not metadata_path.exists():
                return None

            with open(metadata_path) as f:
                metadata_dict = json.load(f)

            # Convert paths back to Path objects
            metadata_dict["file_path"] = Path(metadata_dict["file_path"])
            if metadata_dict.get("parent_file"):
                metadata_dict["parent_file"] = Path(metadata_dict["parent_file"])
            if metadata_dict.get("child_files"):
                metadata_dict["child_files"] = {Path(p) for p in metadata_dict["child_files"]}
            if metadata_dict.get("embedded_files"):
                metadata_dict["embedded_files"] = {Path(p) for p in metadata_dict["embedded_files"]}
            if metadata_dict.get("output_files"):
                metadata_dict["output_files"] = {Path(p) for p in metadata_dict["output_files"]}

            return metadata_class.model_validate(metadata_dict)

        except Exception as e:
            logger.error(f"Failed to load metadata for {file_path}: {e}")
            return None

    def delete(self, file_path: Union[str, Path]) -> bool:
        """Delete metadata from store.

        Args:
            file_path: Path to original file

        Returns:
            bool: Whether deletion was successful
        """
        try:
            metadata_path = self._get_metadata_path(file_path)
            if metadata_path.exists():
                metadata_path.unlink()

            # Remove from index
            self.index.remove_metadata(file_path)
            
            return True

        except Exception as e:
            logger.error(f"Failed to delete metadata for {file_path}: {e}")
            return False

    def search(self, query: str) -> List[BaseMetadata]:
        """Search metadata store.

        Args:
            query: Search query

        Returns:
            List[BaseMetadata]: List of matching metadata
        """
        try:
            results = self.index.search(query)
            return [self.load(r.file_path) for r in results if r]
        except Exception as e:
            logger.error(f"Failed to search metadata store: {e}")
            return []

    def _get_metadata_path(self, file_path: Union[str, Path]) -> Path:
        """Get path where metadata file should be stored.

        Args:
            file_path: Path to original file

        Returns:
            Path: Path where metadata should be stored
        """
        file_path = Path(file_path)
        return self.store_dir / f"{file_path.stem}.json" 