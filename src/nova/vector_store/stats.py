"""Statistics for vector store operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VectorStoreStats:
    """Track statistics for vector store operations."""

    def __init__(self, vector_dir: str | None = None) -> None:
        """Initialize statistics."""
        self.vector_dir = Path(vector_dir) if vector_dir else None
        self.stats_file = self.vector_dir / "stats.json" if self.vector_dir else None

        # Basic stats
        self.total_chunks = 0
        self.total_searches = 0
        self.total_errors = 0
        self.total_results = 0

        # Content stats
        self.unique_sources: set[str] = set()
        self.unique_tags: set[str] = set()
        self.total_attachments = 0
        self.attachment_types: dict[str, int] = {}

        # Date tracking
        self.earliest_date: str | None = None
        self.latest_date: str | None = None
        self.last_update: str | None = None

        # Load existing stats if available
        self._load_stats()

    def _load_stats(self) -> None:
        """Load statistics from file."""
        if not self.stats_file or not self.stats_file.exists():
            return

        try:
            with open(self.stats_file, encoding="utf-8") as f:
                stats = json.load(f)
                # Basic stats
                self.total_chunks = stats.get("total_chunks", 0)
                self.total_searches = stats.get("total_searches", 0)
                self.total_errors = stats.get("total_errors", 0)
                self.total_results = stats.get("total_results", 0)

                # Content stats
                self.unique_sources = set(stats.get("unique_sources", []))
                self.unique_tags = set(stats.get("unique_tags", []))
                self.total_attachments = stats.get("total_attachments", 0)
                self.attachment_types = stats.get("attachment_types", {})

                # Date tracking
                self.earliest_date = stats.get("earliest_date")
                self.latest_date = stats.get("latest_date")
                self.last_update = stats.get("last_update")
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")

    def _save_stats(self) -> None:
        """Save statistics to file."""
        if not self.stats_file:
            return

        try:
            stats = {
                # Basic stats
                "total_chunks": self.total_chunks,
                "total_searches": self.total_searches,
                "total_errors": self.total_errors,
                "total_results": self.total_results,
                # Content stats
                "unique_sources": list(self.unique_sources),
                "unique_tags": list(self.unique_tags),
                "total_attachments": self.total_attachments,
                "attachment_types": self.attachment_types,
                # Date tracking
                "earliest_date": self.earliest_date,
                "latest_date": self.latest_date,
                "last_update": datetime.now().isoformat(),
            }

            # Create directory if it doesn't exist
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def record_chunk_added(self, metadata: dict[str, Any]) -> None:
        """Record that a chunk was added with its metadata."""
        self.total_chunks += 1

        # Track source
        source = metadata.get("source", "")
        if source:
            self.unique_sources.add(source)

        # Track tags
        tags = json.loads(metadata.get("tags", "[]"))
        if tags:
            self.unique_tags.update(tags)

        # Track attachments
        attachments = json.loads(metadata.get("attachments", "[]"))
        if attachments:
            self.total_attachments += len(attachments)
            for att in attachments:
                att_type = att.get("type", "unknown")
                self.attachment_types[att_type] = self.attachment_types.get(att_type, 0) + 1

        # Track dates
        date_str = metadata.get("date")
        if date_str:
            if not self.earliest_date or date_str < self.earliest_date:
                self.earliest_date = date_str
            if not self.latest_date or date_str > self.latest_date:
                self.latest_date = date_str

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

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return {
            # Basic stats
            "total_chunks": self.total_chunks,
            "total_searches": self.total_searches,
            "total_errors": self.total_errors,
            "total_results": self.total_results,
            # Content stats
            "unique_sources": len(self.unique_sources),
            "unique_tags": len(self.unique_tags),
            "total_attachments": self.total_attachments,
            "attachment_types": self.attachment_types,
            # Date tracking
            "earliest_date": self.earliest_date,
            "latest_date": self.latest_date,
            "last_update": self.last_update,
            # Additional metrics
            "avg_results_per_search": round(self.total_results / self.total_searches, 2)
            if self.total_searches > 0
            else 0,
            "error_rate": round((self.total_errors / self.total_chunks * 100), 2)
            if self.total_chunks > 0
            else 0,
            "tags_list": sorted(list(self.unique_tags)),
        }
