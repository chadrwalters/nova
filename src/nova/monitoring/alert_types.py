"""Shared alert types and data classes."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from collections import defaultdict

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status values."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

@dataclass
class Alert:
    """Alert data class."""
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None

@dataclass
class AlertGroup:
    """Group of related alerts."""
    group_id: str
    alert_type: str
    component: str
    severity: AlertSeverity
    alerts: List['Alert']
    first_seen: datetime
    last_seen: datetime
    total_alerts: int
    active_alerts: int
    related_components: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Initialize related components from alerts."""
        # Find all components that share the same alert type
        self.related_components = {
            alert.component for alert in self.alerts
        }
        # Add any other components that were passed in
        if not isinstance(self.related_components, set):
            self.related_components = set(self.related_components)
        if self.component not in self.related_components:
            self.related_components.add(self.component)

    @property
    def count(self) -> int:
        """Total number of alerts in the group."""
        return len(self.alerts)

@dataclass
class AlertTrend:
    """Trend in alert patterns over time."""
    trend_id: str
    alert_type: str
    component: str
    severity: AlertSeverity
    start_time: datetime
    end_time: datetime
    alert_count: int
    rate_of_change: float
    is_increasing: bool
    severity_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def __post_init__(self):
        """Initialize severity counts if not provided."""
        if not isinstance(self.severity_counts, defaultdict):
            self.severity_counts = defaultdict(int, self.severity_counts)
