"""Logging configuration and setup."""

import logging
import re
import sys
from pathlib import Path
from typing import Any, List, Optional, TypeAlias, Union, cast, Pattern

import structlog
from structlog import PrintLoggerFactory, configure, dev, make_filtering_bound_logger
from structlog.contextvars import merge_contextvars
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    add_log_level,
    format_exc_info,
)
from structlog.stdlib import BoundLogger
from structlog.types import EventDict, Processor

# Type aliases
LogLevel: TypeAlias = Union[str, int]
LogHandler: TypeAlias = logging.Handler
LogConfig: TypeAlias = dict[str, Any]
Processors: TypeAlias = list[Processor]


class BinaryContentFilter(logging.Filter):
    def __init__(
        self,
        name: str = "",
        pattern: str = r"[A-Za-z0-9+/]{100,}={0,2}",
        summary_template: str = "[BASE64 DATA: {size} bytes]"
    ):
        super().__init__(name)
        self.pattern: Pattern = re.compile(pattern)
        self.summary_template = summary_template

    def _filter_string(self, text: str) -> str:
        """Filter base64 content from a single string."""
        if not isinstance(text, str):
            return text
            
        matches = list(self.pattern.finditer(text))
        if not matches:
            return text
            
        result = text
        for match in matches:
            base64_content = match.group(0)
            summary = self.summary_template.format(size=len(base64_content))
            result = result.replace(base64_content, summary)
        return result

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter the log record, replacing base64 content with summaries."""
        # Filter the main message
        if isinstance(record.msg, str):
            record.msg = self._filter_string(record.msg)
            
        # Filter any string arguments
        if record.args:
            if isinstance(record.args, (tuple, list)):
                record.args = tuple(
                    self._filter_string(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: self._filter_string(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
                
        return True


def setup_logging(
    log_level: LogLevel = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = False,
) -> None:
    """Set up unified logging configuration."""
    
    # Create binary content filter
    binary_filter = BinaryContentFilter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.addFilter(binary_filter)  # Add filter to handler
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add console handler to root logger
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(filename=log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(binary_filter)  # Add filter to file handler
        root_logger.addHandler(file_handler)


def get_logger(name: Optional[str] = None) -> BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (if None, uses calling module name)

    Returns:
        Configured logger instance
    """
    return cast(BoundLogger, structlog.get_logger(name))


def get_file_logger(name: str) -> structlog.BoundLogger:
    """Get a logger configured for file operations.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
    """
    return structlog.get_logger(name).bind(
        component="file_operations"
    )

def log_file_operation(
    logger: structlog.BoundLogger,
    operation: str,
    file_path: Path,
    category: str,
    **kwargs
) -> None:
    """Log a file operation with consistent formatting.
    
    Args:
        logger: Logger instance
        operation: Operation being performed (read/write/create/delete)
        file_path: Path to file
        category: File category (markdown/html/pdf/temp)
        **kwargs: Additional logging context
    """
    logger.info(
        f"{operation} {category} file",
        path=str(file_path),
        operation=operation,
        category=category,
        **kwargs
    )


# Type hints for exports
__all__: list[str] = ["setup_logging", "get_logger"]
