"""Monitoring utilities for the Nova document processing pipeline."""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: float
    value: Union[float, int, str]
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class Metric:
    """A time series metric."""
    name: str
    points: List[MetricPoint] = field(default_factory=list)
    description: str = ""

class MonitoringManager:
    """Manages monitoring and metrics collection."""
    
    def __init__(self, metrics_dir: Union[str, Path]) -> None:
        """Initialize monitoring manager.
        
        Args:
            metrics_dir: Directory to store metrics data
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: Dict[str, Metric] = {}
        
        # Load existing metrics
        self._load_metrics()
        
        # Initialize standard metrics
        self._init_standard_metrics()
        
        logger.debug("Initialized MonitoringManager with metrics directory: %s", self.metrics_dir)
    
    def _init_standard_metrics(self) -> None:
        """Initialize standard metrics."""
        self.add_metric("api_calls", "Number of API calls made")
        self.add_metric("api_latency", "API call latency in seconds")
        self.add_metric("image_processing_time", "Time taken to process images in seconds")
        self.add_metric("cache_hits", "Number of cache hits")
        self.add_metric("cache_misses", "Number of cache misses")
        self.add_metric("errors", "Number of errors encountered")
    
    def _get_metric_file(self, name: str) -> Path:
        """Get the path to a metric's data file."""
        return self.metrics_dir / f"{name}.json"
    
    def _load_metrics(self) -> None:
        """Load metrics from disk."""
        try:
            for metric_file in self.metrics_dir.glob("*.json"):
                try:
                    with open(metric_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name = data.get('name')
                        if name:
                            points = []
                            for point_data in data.get('points', []):
                                points.append(MetricPoint(
                                    timestamp=point_data['timestamp'],
                                    value=point_data['value'],
                                    tags=point_data.get('tags', {})
                                ))
                            self.metrics[name] = Metric(
                                name=name,
                                points=points,
                                description=data.get('description', '')
                            )
                            logger.debug("Loaded metric %s with %d points", name, len(points))
                except Exception as e:
                    logger.warning("Failed to load metric file %s: %s", metric_file, e)
        except Exception as e:
            logger.warning("Failed to load metrics: %s", e)
    
    def _save_metric(self, name: str) -> None:
        """Save a metric to disk."""
        try:
            metric = self.metrics.get(name)
            if metric:
                metric_file = self._get_metric_file(name)
                data = {
                    'name': metric.name,
                    'description': metric.description,
                    'points': [
                        {
                            'timestamp': p.timestamp,
                            'value': p.value,
                            'tags': p.tags
                        }
                        for p in metric.points
                    ]
                }
                with open(metric_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                logger.debug("Saved metric %s with %d points", name, len(metric.points))
        except Exception as e:
            logger.warning("Failed to save metric %s: %s", name, e)
    
    def add_metric(self, name: str, description: str = "") -> None:
        """Add a new metric.
        
        Args:
            name: Metric name
            description: Metric description
        """
        if name not in self.metrics:
            self.metrics[name] = Metric(name=name, description=description)
            self._save_metric(name)
            logger.debug("Added new metric: %s", name)
    
    def record_metric(self, name: str, value: Union[float, int, str], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags to associate with the metric
        """
        if name not in self.metrics:
            self.add_metric(name)
        
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )
        self.metrics[name].points.append(point)
        self._save_metric(name)
        logger.debug("Recorded metric %s: %s", name, value)
    
    def get_metric(self, name: str, start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[MetricPoint]:
        """Get metric points within the specified time range.
        
        Args:
            name: Metric name
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
        
        Returns:
            List of metric points
        """
        if name not in self.metrics:
            return []
        
        points = self.metrics[name].points
        if start_time is not None:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time is not None:
            points = [p for p in points if p.timestamp <= end_time]
        
        return points
    
    def get_metric_summary(self, name: str, start_time: Optional[float] = None, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Get summary statistics for a metric.
        
        Args:
            name: Metric name
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
        
        Returns:
            Dictionary containing summary statistics
        """
        points = self.get_metric(name, start_time, end_time)
        if not points:
            return {
                'count': 0,
                'first_timestamp': None,
                'last_timestamp': None,
                'min': None,
                'max': None,
                'avg': None
            }
        
        values = [p.value for p in points if isinstance(p.value, (int, float))]
        return {
            'count': len(points),
            'first_timestamp': datetime.fromtimestamp(points[0].timestamp).isoformat(),
            'last_timestamp': datetime.fromtimestamp(points[-1].timestamp).isoformat(),
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'avg': sum(values) / len(values) if values else None
        }
    
    def get_all_metrics_summary(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Get summary statistics for all metrics.
        
        Args:
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
        
        Returns:
            Dictionary containing summary statistics for all metrics
        """
        return {
            name: self.get_metric_summary(name, start_time, end_time)
            for name in self.metrics
        }
    
    def clear_metrics(self, older_than: Optional[float] = None) -> None:
        """Clear metrics data.
        
        Args:
            older_than: Clear metrics older than this timestamp
        """
        if older_than is not None:
            for name, metric in self.metrics.items():
                metric.points = [p for p in metric.points if p.timestamp >= older_than]
                self._save_metric(name)
            logger.debug("Cleared metrics older than %s", datetime.fromtimestamp(older_than).isoformat())
        else:
            for name in list(self.metrics.keys()):
                metric_file = self._get_metric_file(name)
                try:
                    if metric_file.exists():
                        metric_file.unlink()
                except Exception as e:
                    logger.warning("Failed to delete metric file %s: %s", metric_file, e)
            self.metrics.clear()
            logger.debug("Cleared all metrics") 