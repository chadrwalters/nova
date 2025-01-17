"""Statistics for vector store operations."""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStoreStats:
    """Track statistics for vector store operations."""

    def __init__(self, vector_dir: str | None = None) -> None:
        """Initialize statistics."""
        self.vector_dir = Path(vector_dir) if vector_dir else None
        self.stats_file = self.vector_dir / "stats.json" if self.vector_dir else None
        self.total_chunks = 0
        self.total_searches = 0
        self.total_errors = 0
        self.total_results = 0
        self.last_update = None

        # Load existing stats if available
        self._load_stats()

    def _load_stats(self) -> None:
        """Load statistics from file."""
        if not self.stats_file or not self.stats_file.exists():
            return

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
                self.total_chunks = stats.get("total_chunks", 0)
                self.total_searches = stats.get("total_searches", 0)
                self.total_errors = stats.get("total_errors", 0)
                self.total_results = stats.get("total_results", 0)
                self.last_update = stats.get("last_update")
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")

    def _save_stats(self) -> None:
        """Save statistics to file."""
        if not self.stats_file:
            return

        try:
            stats = {
                "total_chunks": self.total_chunks,
                "total_searches": self.total_searches,
                "total_errors": self.total_errors,
                "total_results": self.total_results,
                "last_update": datetime.now().isoformat(),
            }

            # Create directory if it doesn't exist
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def record_chunk_added(self) -> None:
        """Record that a chunk was added."""
        self.total_chunks += 1
        self._save_stats()

    def record_search(self, num_results: int) -> None:
        """Record a search operation."""
        self.total_searches += 1
        self.total_results += num_results
        self._save_stats()

    def record_error(self) -> None:
        """Record an error."""
        self.total_errors += 1
        self._save_stats()

    def get_stats(self) -> dict[str, int | str | None]:
        """Get current statistics."""
        return {
            "total_chunks": self.total_chunks,
            "total_searches": self.total_searches,
            "total_errors": self.total_errors,
            "total_results": self.total_results,
            "last_update": self.last_update,
        }
