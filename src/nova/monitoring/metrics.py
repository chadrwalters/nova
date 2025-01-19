"""Session metrics for Nova system."""

from datetime import datetime


class SessionMetrics:
    """Tracks session-level metrics."""

    def __init__(self, start_time: datetime):
        """Initialize session metrics.

        Args:
            start_time: Session start time
        """
        # Base metrics
        self.start_time = start_time
        self.queries_processed = 0
        self.total_query_time = 0.0
        self.peak_memory_mb = 0.0
        self.errors_encountered = 0
        self.last_error_time: datetime | None = None
        self.last_error_message: str | None = None

        # Rebuild metrics
        self.rebuild_start_time: datetime | None = None
        self.rebuild_end_time: datetime | None = None
        self.chunks_processed = 0
        self.total_chunks = 0
        self.processing_time = 0.0
        self.rebuild_errors = 0
        self.rebuild_last_error_time: datetime | None = None
        self.rebuild_last_error_message: str | None = None
        self.rebuild_peak_memory_mb = 0.0
