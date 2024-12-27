"""State tracking models."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class HandlerState:
    """Handler processing state."""
    processed_files: Set[Path] = field(default_factory=set)
    failed_files: Set[Path] = field(default_factory=set)
    skipped_files: Set[Path] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    _data: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __getitem__(self, key: str) -> Any:
        """Get item from state data."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in state data."""
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete item from state data."""
        del self._data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in state data."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get item from state data with default value."""
        return self._data.get(key, default)

    def add_processed_file(self, file_path: Path) -> None:
        """Add a successfully processed file."""
        self.processed_files.add(file_path)

    def add_failed_file(self, file_path: Path) -> None:
        """Add a failed file."""
        self.failed_files.add(file_path)

    def add_skipped_file(self, file_path: Path) -> None:
        """Add a skipped file."""
        self.skipped_files.add(file_path)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def add_metric(self, key: str, value: Any) -> None:
        """Add a metric."""
        self.metrics[key] = value

    def start(self) -> None:
        """Mark state start time."""
        self.start_time = datetime.now()

    def end(self) -> None:
        """Mark state end time."""
        self.end_time = datetime.now()

    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None 