"""Structured logging with JSON format, rotation, and aggregation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import json
import logging
import time

from .metrics import MetricsTracker


@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: datetime
    level: str
    message: str
    logger: str
    source: Dict[str, str]
    context: Dict[str, Any]
    metrics: Dict[str, Any]
    tags: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger": self.logger,
            "source": self.source,
            "context": self.context,
            "metrics": self.metrics,
            "tags": self.tags
        }


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def __init__(self, include_source: bool = True):
        """Initialize formatter.
        
        Args:
            include_source: Whether to include source information
        """
        super().__init__()
        self.include_source = include_source
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted string
        """
        data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        
        if self.include_source:
            data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
            
        if hasattr(record, "context"):
            data["context"] = record.context
            
        if hasattr(record, "metrics"):
            data["metrics"] = record.metrics
            
        if hasattr(record, "tags"):
            data["tags"] = record.tags
            
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(data)


class LogAggregator:
    """Aggregates and analyzes log records."""
    
    def __init__(self, metrics_dir: Optional[Union[str, Path]] = None):
        """Initialize log aggregator.
        
        Args:
            metrics_dir: Optional directory for metrics storage
        """
        # Create metrics directory if specified
        metrics_path = Path(metrics_dir) if metrics_dir else Path.cwd() / "metrics" / "log_aggregator"
        self.metrics = MetricsTracker(metrics_dir=metrics_path)
        
        self.records: List[LogRecord] = []
        self.start_time = datetime.now()
        
    def add_record(self, record: LogRecord) -> None:
        """Add a log record.
        
        Args:
            record: Log record to add
        """
        self.records.append(record)
        
        # Update metrics
        self.metrics.increment(f"log_level_{record.level.lower()}", 1)
        if record.metrics:
            for key, value in record.metrics.items():
                self.metrics.gauge(f"log_metric_{key}", value)
                
    def get_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        levels: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> List[LogRecord]:
        """Get filtered log records.
        
        Args:
            start_time: Start time filter
            end_time: End time filter
            levels: List of log levels to include
            tags: Tags to filter by
            
        Returns:
            List of filtered log records
        """
        filtered = self.records
        
        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]
        if levels:
            filtered = [r for r in filtered if r.level in levels]
        if tags:
            filtered = [
                r for r in filtered
                if all(r.tags.get(k) == v for k, v in tags.items())
            ]
            
        return filtered
        
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get log statistics.
        
        Args:
            start_time: Start time for statistics
            end_time: End time for statistics
            
        Returns:
            Dictionary of statistics
        """
        records = self.get_records(start_time, end_time)
        
        stats = {
            "total_records": len(records),
            "levels": {},
            "loggers": set(),
            "tags": set()
        }
        
        for record in records:
            # Count by level
            level = record.level
            stats["levels"][level] = stats["levels"].get(level, 0) + 1
            
            # Track unique loggers
            stats["loggers"].add(record.logger)
            
            # Track unique tags
            stats["tags"].update(record.tags.keys())
            
        # Calculate rates
        if records:
            duration = (records[-1].timestamp - records[0].timestamp).total_seconds()
            if duration > 0:
                stats["records_per_second"] = len(records) / duration
                
        return stats


class StructuredLogger:
    """Enhanced logger with structured logging and aggregation."""
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        metrics_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            level: Log level
            metrics_dir: Optional directory for metrics storage
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create metrics directory if specified
        metrics_path = Path(metrics_dir) if metrics_dir else Path.cwd() / "metrics" / name.lower()
        self.metrics = MetricsTracker(metrics_dir=metrics_path)
        
        self.context: Dict[str, Any] = {}
        self.tags: Dict[str, str] = {}
        
    def set_context(self, **kwargs: Any) -> None:
        """Set context values.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)
        
    def set_tags(self, **kwargs: str) -> None:
        """Set tag values.
        
        Args:
            **kwargs: Tag key-value pairs
        """
        self.tags.update(kwargs)
        
    def _log(
        self,
        level: int,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log a message with context and metrics.
        
        Args:
            level: Log level
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        if not self.logger.isEnabledFor(level):
            return
            
        # Merge context and tags
        record_context = self.context.copy()
        if context:
            record_context.update(context)
            
        record_tags = self.tags.copy()
        if tags:
            record_tags.update(tags)
            
        # Create log record
        record = logging.LogRecord(
            name=self.name,
            level=level,
            pathname=kwargs.get("pathname", ""),
            lineno=kwargs.get("lineno", 0),
            msg=msg,
            args=args,
            exc_info=kwargs.get("exc_info"),
            func=kwargs.get("func", ""),
            sinfo=kwargs.get("sinfo")
        )
        
        # Add extra attributes
        record.context = record_context
        record.metrics = metrics or {}
        record.tags = record_tags
        
        # Log the record
        self.logger.handle(record)
        
        # Update metrics
        if metrics:
            for key, value in metrics.items():
                self.metrics.gauge(f"log_metric_{key}", value)
                
    def debug(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log a debug message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        self._log(logging.DEBUG, msg, *args, context=context, metrics=metrics, tags=tags, **kwargs)
        
    def info(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log an info message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        self._log(logging.INFO, msg, *args, context=context, metrics=metrics, tags=tags, **kwargs)
        
    def warning(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log a warning message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        self._log(logging.WARNING, msg, *args, context=context, metrics=metrics, tags=tags, **kwargs)
        
    def error(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log an error message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        self._log(logging.ERROR, msg, *args, context=context, metrics=metrics, tags=tags, **kwargs)
        
    def critical(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log a critical message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Additional context
            metrics: Metrics to record
            tags: Additional tags
            **kwargs: Additional logging arguments
        """
        self._log(logging.CRITICAL, msg, *args, context=context, metrics=metrics, tags=tags, **kwargs) 