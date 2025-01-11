"""Alert aggregation and correlation for Nova monitoring."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging
import time
import uuid

from nova.monitoring.alert_types import (
    Alert, AlertGroup, AlertTrend,
    AlertSeverity, AlertStatus
)
from nova.monitoring.alert_storage import AlertStorage, StoredAlert

logger = logging.getLogger(__name__)

class AlertAggregator:
    """Aggregates alerts to identify patterns and trends."""

    def __init__(self, alert_storage: AlertStorage):
        """Initialize the alert aggregator.

        Args:
            alert_storage: Storage for retrieving alerts.
        """
        self.alert_storage = alert_storage

    def group_alerts(
        self,
        time_window: timedelta = timedelta(hours=1),
        min_group_size: int = 2
    ) -> List[AlertGroup]:
        """Group alerts by type and component within a specified time window.

        Args:
            time_window: Time window to consider for grouping alerts.
            min_group_size: Minimum number of alerts required to form a group.

        Returns:
            List of AlertGroup objects for groups that meet the minimum size.
        """
        alerts = self.alert_storage.get_alerts()
        cutoff = datetime.now(timezone.utc) - time_window

        # Group alerts by type and component
        groups = defaultdict(list)
        for alert in alerts:
            if alert.created_at >= cutoff:
                groups[(alert.type, alert.component)].append(alert)

        # Create alert groups that meet the minimum size requirement
        alert_groups = []
        for (alert_type, component), group_alerts in groups.items():
            if len(group_alerts) >= min_group_size:
                # Find all components that have alerts of the same type
                related_components = {alert.component for alert in alerts if alert.type == alert_type}
                related_components.add(component)  # Ensure current component is included

                # Calculate maximum severity from recent alerts
                max_severity = max((alert.severity for alert in group_alerts), default=AlertSeverity.INFO)

                # Calculate first and last seen timestamps
                first_seen = min(alert.created_at for alert in group_alerts)
                last_seen = max(alert.created_at for alert in group_alerts)

                # Count active alerts
                active_alerts = sum(1 for alert in group_alerts if alert.status == AlertStatus.ACTIVE)

                alert_group = AlertGroup(
                    group_id=str(uuid.uuid4()),
                    alert_type=alert_type,
                    component=component,
                    severity=max_severity,
                    alerts=group_alerts,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    total_alerts=len(group_alerts),
                    active_alerts=active_alerts,
                    related_components=related_components
                )
                alert_groups.append(alert_group)

        return alert_groups

    def get_component_correlations(
        self,
        time_window: timedelta = timedelta(hours=1),
        correlation_threshold: int = 2
    ) -> Dict[str, Set[str]]:
        """Find correlated components based on alert patterns.

        Args:
            time_window: Time window for correlation analysis
            correlation_threshold: Minimum number of shared alert types for correlation

        Returns:
            Dictionary mapping components to their correlated components
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - time_window

        alerts = self.alert_storage.get_alerts(
            start_time=start_time,
            end_time=end_time
        )

        # Build component alert type sets
        component_alerts: Dict[str, Set[str]] = defaultdict(set)
        for alert in alerts:
            component_alerts[alert.component].add(alert.type)

        # Find correlations
        correlations: Dict[str, Set[str]] = defaultdict(set)
        components = list(component_alerts.keys())

        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                shared_types = len(component_alerts[comp1] & component_alerts[comp2])
                if shared_types >= correlation_threshold:
                    correlations[comp1].add(comp2)
                    correlations[comp2].add(comp1)

        return correlations

    def analyze_trends(
        self,
        time_windows: List[timedelta] = [
            timedelta(hours=1),
            timedelta(hours=6),
            timedelta(hours=24)
        ]
    ) -> Dict[timedelta, List[AlertTrend]]:
        """Analyze alert trends over different time windows."""
        trends: Dict[timedelta, List[AlertTrend]] = {}

        for window in time_windows:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - window
            mid_time = start_time + (window / 2)

            # Get alerts for the full window
            alerts = self.alert_storage.get_alerts(
                start_time=start_time,
                end_time=end_time
            )

            # Group by type and component
            alert_groups: Dict[Tuple[str, str], List[StoredAlert]] = defaultdict(list)
            for alert in alerts:
                key = (alert.type, alert.component)
                alert_groups[key].append(alert)

            window_trends = []
            for (alert_type, component), group_alerts in alert_groups.items():
                # Count alerts in each half of the window
                first_half = sum(1 for a in group_alerts if a.created_at < mid_time)
                second_half = len(group_alerts) - first_half

                # Calculate rate of change (alerts per hour)
                hours = window.total_seconds() / 3600
                rate = (second_half - first_half) / hours

                # Get max severity and count by severity
                max_severity = max(a.severity for a in group_alerts)
                severity_counts = defaultdict(int)
                for alert in group_alerts:
                    severity_counts[alert.severity.value.lower()] += 1

                trend = AlertTrend(
                    trend_id=f"{alert_type}_{component}_{window.total_seconds()}",
                    alert_type=alert_type,
                    component=component,
                    severity=max_severity,
                    start_time=start_time,
                    end_time=end_time,
                    alert_count=len(group_alerts),
                    rate_of_change=rate,
                    is_increasing=second_half > first_half,
                    severity_counts=severity_counts
                )
                window_trends.append(trend)

            trends[window] = sorted(window_trends, key=lambda t: t.alert_count, reverse=True)

        return trends
