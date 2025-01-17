"""Statistics for vector store operations."""


class VectorStoreStats:
    """Track statistics for vector store operations."""

    def __init__(self) -> None:
        """Initialize statistics."""
        self.total_chunks = 0
        self.total_searches = 0
        self.total_errors = 0
        self.total_results = 0

    def record_chunk_added(self) -> None:
        """Record a chunk being added."""
        self.total_chunks += 1

    def record_search_result(self, num_results: int) -> None:
        """Record a successful search with results."""
        self.total_searches += 1
        self.total_results += num_results

    def record_search_error(self) -> None:
        """Record a search error."""
        self.total_errors += 1

    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            "total_chunks": self.total_chunks,
            "total_searches": self.total_searches,
            "total_errors": self.total_errors,
            "total_results": self.total_results,
            "avg_results_per_search": self.total_results / max(1, self.total_searches),
        }
