"""Health warning system for Nova.

This module provides warning detection and tracking capabilities for
various system health metrics including memory usage, disk space, and
vector store status.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WarningSeverity(Enum):
    """Warning severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WarningCategory(Enum):
    """Categories of warnings."""

    MEMORY = "memory"
    DISK = "disk"
    CPU = "cpu"
    DIRECTORY = "directory"
    VECTOR_STORE = "vector_store"
    METADATA = "metadata"


@dataclass
class WarningThresholds:
    """System warning thresholds."""

    # Memory thresholds (MB)
    memory_warning_mb: float = 1024.0  # 1GB
    memory_critical_mb: float = 1536.0  # 1.5GB
    sustained_memory_minutes: int = 5

    # Disk thresholds
    disk_warning_percent: float = 80.0
    disk_critical_percent: float = 90.0
    min_free_space_gb: float = 5.0

    # CPU thresholds
    cpu_warning_percent: float = 70.0
    cpu_critical_percent: float = 85.0
    sustained_cpu_minutes: int = 5

    # Vector store thresholds
    max_vector_store_size_gb: float = 10.0
    max_error_rate_percent: float = 5.0
    min_search_performance_ms: float = 100.0

    def to_dict(self) -> dict[str, float]:
        """Convert thresholds to dictionary.

        Returns:
            Dictionary of threshold values
        """
        return {
            "memory_warning_mb": self.memory_warning_mb,
            "memory_critical_mb": self.memory_critical_mb,
            "sustained_memory_minutes": self.sustained_memory_minutes,
            "disk_warning_percent": self.disk_warning_percent,
            "disk_critical_percent": self.disk_critical_percent,
            "min_free_space_gb": self.min_free_space_gb,
            "cpu_warning_percent": self.cpu_warning_percent,
            "cpu_critical_percent": self.cpu_critical_percent,
            "sustained_cpu_minutes": self.sustained_cpu_minutes,
            "max_vector_store_size_gb": self.max_vector_store_size_gb,
            "max_error_rate_percent": self.max_error_rate_percent,
            "min_search_performance_ms": self.min_search_performance_ms,
        }


@dataclass
class Warning:
    """System warning."""

    category: WarningCategory
    severity: WarningSeverity
    message: str
    timestamp: datetime
    details: dict[str, str] | None = None
    resolved: bool = False
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert warning to dictionary.

        Returns:
            Dictionary representation of warning
        """
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {},
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class HealthWarningSystem:
    """System health warning detection and tracking."""

    def __init__(
        self,
        base_path: Path,
        thresholds: WarningThresholds | None = None,
    ) -> None:
        """Initialize warning system.

        Args:
            base_path: Base path for Nova system
            thresholds: Optional custom warning thresholds
        """
        self.base_path = base_path
        self.warnings_file = base_path / ".nova" / "warnings.json"
        self.thresholds = thresholds or WarningThresholds()

        # Active warnings
        self._active_warnings: list[Warning] = []
        self._warning_history: list[Warning] = []

        # Warning tracking
        self._memory_warning_start: datetime | None = None
        self._cpu_warning_start: datetime | None = None
        self._seen_warnings: set[str] = set()

        # Create directory if needed
        self.warnings_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing warnings
        self._load_warnings()

    def _load_warnings(self) -> None:
        """Load warnings from file."""
        if not self.warnings_file.exists():
            logger.info("No existing warnings file found")
            return

        try:
            with open(self.warnings_file, encoding="utf-8") as f:
                data = json.load(f)

            # Load active warnings
            for warning_data in data.get("active", []):
                warning = Warning(
                    category=WarningCategory(warning_data["category"]),
                    severity=WarningSeverity(warning_data["severity"]),
                    message=warning_data["message"],
                    timestamp=datetime.fromisoformat(warning_data["timestamp"]),
                    details=warning_data.get("details"),
                )
                self._active_warnings.append(warning)

            # Load warning history
            for warning_data in data.get("history", []):
                warning = Warning(
                    category=WarningCategory(warning_data["category"]),
                    severity=WarningSeverity(warning_data["severity"]),
                    message=warning_data["message"],
                    timestamp=datetime.fromisoformat(warning_data["timestamp"]),
                    details=warning_data.get("details"),
                    resolved=warning_data["resolved"],
                    resolved_at=datetime.fromisoformat(warning_data["resolved_at"])
                    if warning_data.get("resolved_at")
                    else None,
                )
                self._warning_history.append(warning)

            logger.info(
                f"Loaded {len(self._active_warnings)} active warnings and "
                f"{len(self._warning_history)} historical warnings"
            )
        except Exception as e:
            logger.error(f"Failed to load warnings: {e}", exc_info=True)

    def _save_warnings(self) -> None:
        """Save warnings to file."""
        try:
            data = {
                "active": [w.to_dict() for w in self._active_warnings],
                "history": [w.to_dict() for w in self._warning_history],
            }

            with open(self.warnings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info("Successfully saved warnings")
        except Exception as e:
            logger.error(f"Failed to save warnings: {e}", exc_info=True)

    def add_warning(
        self,
        category: WarningCategory,
        severity: WarningSeverity,
        message: str,
        details: dict[str, str] | None = None,
    ) -> None:
        """Add a new warning.

        Args:
            category: Warning category
            severity: Warning severity level
            message: Warning message
            details: Optional warning details
        """
        # Create warning key for deduplication
        warning_key = f"{category.value}:{severity.value}:{message}"

        # Skip if we've seen this exact warning recently
        if warning_key in self._seen_warnings:
            return

        # Create new warning
        warning = Warning(
            category=category,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            details=details,
        )

        # Add to active warnings
        self._active_warnings.append(warning)
        self._seen_warnings.add(warning_key)

        # Save updated warnings
        self._save_warnings()

        logger.warning(f"{severity.value.upper()} {category.value} warning: {message}")

    def resolve_warning(
        self,
        category: WarningCategory,
        message: str,
    ) -> None:
        """Resolve an active warning.

        Args:
            category: Warning category
            message: Warning message to resolve
        """
        resolved = []
        for warning in self._active_warnings:
            if warning.category == category and warning.message == message:
                warning.resolved = True
                warning.resolved_at = datetime.now()
                resolved.append(warning)

        # Move resolved warnings to history
        for warning in resolved:
            self._active_warnings.remove(warning)
            self._warning_history.append(warning)

            # Remove from seen warnings to allow re-triggering
            warning_key = f"{warning.category.value}:{warning.severity.value}:{warning.message}"
            self._seen_warnings.discard(warning_key)

        if resolved:
            self._save_warnings()
            logger.info(f"Resolved {len(resolved)} warnings for {category.value}")

    def get_active_warnings(
        self,
        category: WarningCategory | None = None,
        severity: WarningSeverity | None = None,
    ) -> list[Warning]:
        """Get active warnings, optionally filtered by category and severity.

        Args:
            category: Optional category to filter by
            severity: Optional severity level to filter by

        Returns:
            List of active warnings matching filters
        """
        warnings = self._active_warnings
        if category:
            warnings = [w for w in warnings if w.category == category]
        if severity:
            warnings = [w for w in warnings if w.severity == severity]
        return warnings

    def get_warning_history(
        self,
        category: WarningCategory | None = None,
        severity: WarningSeverity | None = None,
        limit: int = 100,
    ) -> list[Warning]:
        """Get warning history, optionally filtered and limited.

        Args:
            category: Optional category to filter by
            severity: Optional severity level to filter by
            limit: Maximum number of warnings to return

        Returns:
            List of historical warnings matching filters
        """
        warnings = self._warning_history
        if category:
            warnings = [w for w in warnings if w.category == category]
        if severity:
            warnings = [w for w in warnings if w.severity == severity]
        return warnings[-limit:]  # Return most recent warnings up to limit

    def check_memory_warnings(self, memory_mb: float, peak_mb: float) -> None:
        """Check for memory-related warnings.

        Args:
            memory_mb: Current memory usage in MB
            peak_mb: Peak memory usage in MB
        """
        # Check current memory usage
        if memory_mb >= self.thresholds.memory_critical_mb:
            self.add_warning(
                category=WarningCategory.MEMORY,
                severity=WarningSeverity.CRITICAL,
                message="Critical memory usage detected",
                details={
                    "current_mb": str(round(memory_mb, 2)),
                    "threshold_mb": str(self.thresholds.memory_critical_mb),
                },
            )
        elif memory_mb >= self.thresholds.memory_warning_mb:
            # Track sustained high memory usage
            if not self._memory_warning_start:
                self._memory_warning_start = datetime.now()
            elif (datetime.now() - self._memory_warning_start).total_seconds() >= (
                self.thresholds.sustained_memory_minutes * 60
            ):
                self.add_warning(
                    category=WarningCategory.MEMORY,
                    severity=WarningSeverity.WARNING,
                    message="Sustained high memory usage",
                    details={
                        "current_mb": str(round(memory_mb, 2)),
                        "threshold_mb": str(self.thresholds.memory_warning_mb),
                        "duration_minutes": str(self.thresholds.sustained_memory_minutes),
                    },
                )
        else:
            # Reset tracking if memory usage drops
            self._memory_warning_start = None
            # Resolve any active memory warnings
            self.resolve_warning(
                category=WarningCategory.MEMORY,
                message="Critical memory usage detected",
            )
            self.resolve_warning(
                category=WarningCategory.MEMORY,
                message="Sustained high memory usage",
            )

        # Check peak memory
        if peak_mb >= self.thresholds.memory_critical_mb:
            self.add_warning(
                category=WarningCategory.MEMORY,
                severity=WarningSeverity.WARNING,
                message="Peak memory threshold exceeded",
                details={
                    "peak_mb": str(round(peak_mb, 2)),
                    "threshold_mb": str(self.thresholds.memory_critical_mb),
                },
            )

    def check_disk_warnings(
        self,
        used_percent: float,
        free_gb: float,
        path: str | None = None,
    ) -> None:
        """Check for disk-related warnings.

        Args:
            used_percent: Disk usage percentage
            free_gb: Free space in GB
            path: Optional path being checked
        """
        details = {
            "used_percent": str(round(used_percent, 2)),
            "free_gb": str(round(free_gb, 2)),
        }
        if path:
            details["path"] = path

        # Check usage percentage
        if used_percent >= self.thresholds.disk_critical_percent:
            self.add_warning(
                category=WarningCategory.DISK,
                severity=WarningSeverity.CRITICAL,
                message="Critical disk usage",
                details=details,
            )
        elif used_percent >= self.thresholds.disk_warning_percent:
            self.add_warning(
                category=WarningCategory.DISK,
                severity=WarningSeverity.WARNING,
                message="High disk usage",
                details=details,
            )
        else:
            # Resolve warnings if usage drops
            self.resolve_warning(
                category=WarningCategory.DISK,
                message="Critical disk usage",
            )
            self.resolve_warning(
                category=WarningCategory.DISK,
                message="High disk usage",
            )

        # Check free space
        if free_gb < self.thresholds.min_free_space_gb:
            self.add_warning(
                category=WarningCategory.DISK,
                severity=WarningSeverity.CRITICAL,
                message="Low free disk space",
                details=details,
            )
        else:
            self.resolve_warning(
                category=WarningCategory.DISK,
                message="Low free disk space",
            )

    def check_cpu_warnings(self, cpu_percent: float) -> None:
        """Check for CPU-related warnings.

        Args:
            cpu_percent: CPU usage percentage
        """
        if cpu_percent >= self.thresholds.cpu_critical_percent:
            # Track sustained high CPU usage
            if not self._cpu_warning_start:
                self._cpu_warning_start = datetime.now()
            elif (datetime.now() - self._cpu_warning_start).total_seconds() >= (
                self.thresholds.sustained_cpu_minutes * 60
            ):
                self.add_warning(
                    category=WarningCategory.CPU,
                    severity=WarningSeverity.CRITICAL,
                    message="Sustained critical CPU usage",
                    details={
                        "cpu_percent": str(round(cpu_percent, 2)),
                        "threshold_percent": str(self.thresholds.cpu_critical_percent),
                        "duration_minutes": str(self.thresholds.sustained_cpu_minutes),
                    },
                )
        elif cpu_percent >= self.thresholds.cpu_warning_percent:
            self.add_warning(
                category=WarningCategory.CPU,
                severity=WarningSeverity.WARNING,
                message="High CPU usage",
                details={
                    "cpu_percent": str(round(cpu_percent, 2)),
                    "threshold_percent": str(self.thresholds.cpu_warning_percent),
                },
            )
        else:
            # Reset tracking if CPU usage drops
            self._cpu_warning_start = None
            # Resolve warnings
            self.resolve_warning(
                category=WarningCategory.CPU,
                message="Sustained critical CPU usage",
            )
            self.resolve_warning(
                category=WarningCategory.CPU,
                message="High CPU usage",
            )

    def check_directory_warnings(self, dir_status: dict[str, str]) -> None:
        """Check for directory-related warnings.

        Args:
            dir_status: Dictionary mapping directory names to their status
        """
        for dir_name, status in dir_status.items():
            if status == "missing":
                self.add_warning(
                    category=WarningCategory.DIRECTORY,
                    severity=WarningSeverity.CRITICAL,
                    message=f"Required directory missing: {dir_name}",
                    details={"directory": dir_name, "status": status},
                )
            elif status == "permission_error":
                self.add_warning(
                    category=WarningCategory.DIRECTORY,
                    severity=WarningSeverity.WARNING,
                    message=f"Directory permission error: {dir_name}",
                    details={"directory": dir_name, "status": status},
                )
            elif status == "healthy":
                # Resolve warnings for healthy directories
                self.resolve_warning(
                    category=WarningCategory.DIRECTORY,
                    message=f"Required directory missing: {dir_name}",
                )
                self.resolve_warning(
                    category=WarningCategory.DIRECTORY,
                    message=f"Directory permission error: {dir_name}",
                )

    def check_vector_store_warnings(
        self,
        store_size_gb: float,
        error_rate: float,
        avg_search_time_ms: float,
    ) -> None:
        """Check for vector store-related warnings.

        Args:
            store_size_gb: Vector store size in GB
            error_rate: Error rate as percentage
            avg_search_time_ms: Average search time in milliseconds
        """
        # Check store size
        if store_size_gb >= self.thresholds.max_vector_store_size_gb:
            self.add_warning(
                category=WarningCategory.VECTOR_STORE,
                severity=WarningSeverity.WARNING,
                message="Vector store size limit approaching",
                details={
                    "current_size_gb": str(round(store_size_gb, 2)),
                    "max_size_gb": str(self.thresholds.max_vector_store_size_gb),
                },
            )
        else:
            self.resolve_warning(
                category=WarningCategory.VECTOR_STORE,
                message="Vector store size limit approaching",
            )

        # Check error rate
        if error_rate >= self.thresholds.max_error_rate_percent:
            self.add_warning(
                category=WarningCategory.VECTOR_STORE,
                severity=WarningSeverity.WARNING,
                message="High vector store error rate",
                details={
                    "error_rate_percent": str(round(error_rate, 2)),
                    "threshold_percent": str(self.thresholds.max_error_rate_percent),
                },
            )
        else:
            self.resolve_warning(
                category=WarningCategory.VECTOR_STORE,
                message="High vector store error rate",
            )

        # Check search performance
        if avg_search_time_ms >= self.thresholds.min_search_performance_ms:
            self.add_warning(
                category=WarningCategory.VECTOR_STORE,
                severity=WarningSeverity.WARNING,
                message="Vector store performance degradation",
                details={
                    "avg_search_time_ms": str(round(avg_search_time_ms, 2)),
                    "threshold_ms": str(self.thresholds.min_search_performance_ms),
                },
            )
        else:
            self.resolve_warning(
                category=WarningCategory.VECTOR_STORE,
                message="Vector store performance degradation",
            )

    def check_metadata_warnings(
        self,
        docs_without_tags: int,
        total_docs: int,
        invalid_dates: int,
    ) -> None:
        """Check for metadata-related warnings.

        Args:
            docs_without_tags: Number of documents without tags
            total_docs: Total number of documents
            invalid_dates: Number of documents with invalid dates
        """
        # Check documents without tags
        if docs_without_tags > 0:
            tag_percent = (docs_without_tags / total_docs) * 100 if total_docs > 0 else 0
            if tag_percent >= 20:  # Warning if >20% docs have no tags
                self.add_warning(
                    category=WarningCategory.METADATA,
                    severity=WarningSeverity.WARNING,
                    message="High number of documents without tags",
                    details={
                        "docs_without_tags": str(docs_without_tags),
                        "total_docs": str(total_docs),
                        "percentage": str(round(tag_percent, 2)),
                    },
                )
            else:
                self.resolve_warning(
                    category=WarningCategory.METADATA,
                    message="High number of documents without tags",
                )

        # Check invalid dates
        if invalid_dates > 0:
            date_percent = (invalid_dates / total_docs) * 100 if total_docs > 0 else 0
            if date_percent >= 10:  # Warning if >10% docs have invalid dates
                self.add_warning(
                    category=WarningCategory.METADATA,
                    severity=WarningSeverity.WARNING,
                    message="Documents with invalid dates detected",
                    details={
                        "invalid_dates": str(invalid_dates),
                        "total_docs": str(total_docs),
                        "percentage": str(round(date_percent, 2)),
                    },
                )
            else:
                self.resolve_warning(
                    category=WarningCategory.METADATA,
                    message="Documents with invalid dates detected",
                )
