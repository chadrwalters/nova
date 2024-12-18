"""Logging configuration for Nova Document Processor."""

import logging
from typing import Any, Dict

import structlog
from rich.logging import RichHandler

from .models import LoggingConfig

def setup_logging(config: LoggingConfig, verbose: bool = False) -> None:
    """Configure logging with structlog and rich."""
    
    # Set log level
    level = logging.DEBUG if verbose else getattr(logging, config.level.upper())
    
    # Configure standard logging
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_path=True
            )
        ]
    )

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _filter_binary_data if config.filter_binary else structlog.processors.identity,
        structlog.processors.JSONRenderer() if config.format == "json" else structlog.dev.ConsoleRenderer()
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)

def _filter_binary_data(
    logger: str,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Filter out binary data from logs."""
    MAX_LENGTH = 100  # from config
    
    def _truncate(value: Any) -> str:
        if isinstance(value, bytes):
            return f"[BINARY DATA: {len(value)} bytes]"
        if isinstance(value, str) and len(value) > MAX_LENGTH:
            return f"{value[:MAX_LENGTH]}... [truncated]"
        return value

    return {
        key: _truncate(value)
        for key, value in event_dict.items()
    }