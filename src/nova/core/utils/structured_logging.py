"""Structured logging with JSON format, rotation, and aggregation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import json
import logging
import time

from nova.core.utils.metrics import MetricsTracker


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
    
    def __init__(self, metrics: Optional[MetricsTracker] = None):
        """Initialize log aggregator.
        
        Args:
            metrics: Optional metrics tracker instance
        """
        self.metrics = metrics or MetricsTracker()
        self.records: List[LogRecord] = []
        self.start_time = datetime.now()
        
    def add_record(self, record: LogRecord) -> None:
        """Add a log record.
        
        Args:
            record: Log record to add
        """
        self.records.append(record)
        
        # Update metrics
        self.metrics.increment(f"log_level_{record.level.lower()}")
        if record.metrics:
            for key, value in record.metrics.items():
                self.metrics.set_gauge(f"log_metric_{key}", value)
                
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
        metrics: Optional[MetricsTracker] = None
    ):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            level: Log level
            metrics: Optional metrics tracker instance
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.metrics = metrics or MetricsTracker()
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
        """Internal logging implementation.
        
        Args:
            level: Log level
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        # Update context and tags
        log_context = self.context.copy()
        if context:
            log_context.update(context)
            
        log_tags = self.tags.copy()
        if tags:
            log_tags.update(tags)
            
        # Create record
        record = LogRecord(
            timestamp=datetime.now(),
            level=logging.getLevelName(level),
            message=msg % args if args else msg,
            logger=self.name,
            source={
                "file": kwargs.get("filename", ""),
                "line": kwargs.get("lineno", 0),
                "function": kwargs.get("funcName", "")
            },
            context=log_context,
            metrics=metrics or {},
            tags=log_tags
        )
        
        # Update metrics
        if metrics:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    self.metrics.set_gauge(f"log_metric_{key}", value)
                    
        # Log record
        self.logger.log(level, record.message, **kwargs)
        
    def debug(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log debug message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        self._log(
            logging.DEBUG,
            msg,
            *args,
            context=context,
            metrics=metrics,
            tags=tags,
            **kwargs
        )
        
    def info(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log info message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        self._log(
            logging.INFO,
            msg,
            *args,
            context=context,
            metrics=metrics,
            tags=tags,
            **kwargs
        )
        
    def warning(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log warning message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        self._log(
            logging.WARNING,
            msg,
            *args,
            context=context,
            metrics=metrics,
            tags=tags,
            **kwargs
        )
        
    def error(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log error message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        self._log(
            logging.ERROR,
            msg,
            *args,
            context=context,
            metrics=metrics,
            tags=tags,
            **kwargs
        )
        
    def critical(
        self,
        msg: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Log critical message.
        
        Args:
            msg: Message format string
            *args: Message format arguments
            context: Optional additional context
            metrics: Optional metrics to record
            tags: Optional tags to add
            **kwargs: Additional logging arguments
        """
        self._log(
            logging.CRITICAL,
            msg,
            *args,
            context=context,
            metrics=metrics,
            tags=tags,
            **kwargs
        ) 