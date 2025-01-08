"""Search index for metadata store."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.store.encoders import CustomJSONEncoder

logger = logging.getLogger(__name__)


class SearchResult:
    """Search result from metadata index."""

    def __init__(self, file_path: Path, score: float, metadata: Dict[str, Any]) -> None:
        """Initialize search result.

        Args:
            file_path: Path to original file
            score: Search score
            metadata: Metadata dictionary
        """
        self.file_path = file_path
        self.score = score
        self.metadata = metadata

    def __str__(self) -> str:
        """String representation of search result."""
        return f"SearchResult(file_path={self.file_path}, score={self.score})"


class MetadataIndex:
    """Search index for metadata store."""

    def __init__(self, index_path: Union[str, Path]) -> None:
        """Initialize metadata index.

        Args:
            index_path: Path to index file
        """
        self.index_path = Path(index_path)
        self.index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load index from file."""
        try:
            if self.index_path.exists():
                with open(self.index_path) as f:
                    self.index = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self.index = {}

    def _save_index(self) -> None:
        """Save index to file."""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_path, "w") as f:
                json.dump(self.index, f, cls=CustomJSONEncoder, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def add_metadata(self, metadata: BaseMetadata) -> None:
        """Add metadata to index.

        Args:
            metadata: Metadata to add
        """
        try:
            # Convert metadata to dictionary
            metadata_dict = metadata.model_dump()

            # Add to index
            self.index[str(metadata.file_path)] = {
                "file_path": str(metadata.file_path),
                "title": metadata.title,
                "description": metadata.description,
                "content": metadata.content,
                "tags": list(metadata.tags),
                "metadata": metadata_dict
            }

            # Save index
            self._save_index()

        except Exception as e:
            logger.error(f"Failed to add metadata to index: {e}")

    def remove_metadata(self, file_path: Union[str, Path]) -> None:
        """Remove metadata from index.

        Args:
            file_path: Path to original file
        """
        try:
            # Remove from index
            if str(file_path) in self.index:
                del self.index[str(file_path)]

            # Save index
            self._save_index()

        except Exception as e:
            logger.error(f"Failed to remove metadata from index: {e}")

    def search(self, query: str) -> List[SearchResult]:
        """Search index for metadata.

        Args:
            query: Search query

        Returns:
            List[SearchResult]: List of search results
        """
        try:
            results = []
            query = query.lower()

            for file_path, data in self.index.items():
                score = 0.0

                # Search in title
                if data.get("title") and query in data["title"].lower():
                    score += 1.0

                # Search in description
                if data.get("description") and query in data["description"].lower():
                    score += 0.8

                # Search in content
                if data.get("content") and query in data["content"].lower():
                    score += 0.5

                # Search in tags
                if data.get("tags"):
                    for tag in data["tags"]:
                        if query in tag.lower():
                            score += 0.3

                if score > 0:
                    results.append(SearchResult(
                        file_path=Path(file_path),
                        score=score,
                        metadata=data["metadata"]
                    ))

            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)

            return results

        except Exception as e:
            logger.error(f"Failed to search index: {e}")
            return [] 