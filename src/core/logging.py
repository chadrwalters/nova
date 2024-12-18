import structlog
import logging
import sys
import json
from typing import Any, Dict, Union
from pathlib import Path
import threading
from .base_config import LoggingConfig

# Thread-local storage for logger context
_thread_local = threading.local()

def _json_serializer(obj: Any, **kwargs) -> str:
    """Custom JSON serializer for structlog that handles special types."""
    try:
        if isinstance(obj, (Path, Exception)):
            return str(obj)
        if hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        if isinstance(obj, bytes):
            return f"[BINARY DATA: {len(obj)} bytes]"
        if callable(obj):  # Handle function objects
            if hasattr(obj, '__name__'):
                return f"[FUNCTION: {obj.__name__}]"
            return "[LAMBDA FUNCTION]"  # Handle lambda functions
        if hasattr(obj, '__dict__'):  # Handle custom objects
            return str(obj)
        return str(obj)  # Fall back to string representation
    except Exception as e:
        return f"[UNSERIALIZABLE OBJECT: {str(e)}]"

def configure_logging(config: Union[LoggingConfig, 'NovaConfig'] = None) -> None:
    """Configure structured logging."""
    if config is None:
        config = LoggingConfig()
    
    # Handle both LoggingConfig and NovaConfig objects
    if hasattr(config, 'logging'):
        log_config = config.logging
    else:
        log_config = config

    # Set logging level
    level = getattr(logging, log_config.level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(message)s',
        stream=sys.stdout
    )

    def filter_processor(logger, method_name, event_dict):
        """Filter out large values and sensitive data."""
        result = {}
        for key, value in event_dict.items():
            if key == "config":
                result[key] = "[filtered config]"
            elif callable(value):
                result[key] = "[filtered function]"
            elif isinstance(value, (dict, list)):
                result[key] = "[filtered large object]"
            elif isinstance(value, str) and len(value) > 200:
                result[key] = value[:200] + "..."
            else:
                result[key] = value
        return result

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        filter_processor,
    ]

    # Add renderer based on format
    if log_config.format == "json":
        processors.append(
            structlog.processors.JSONRenderer(
                default=_json_serializer
            )
        )
    else:
        # Define ANSI color codes
        COLORS = {
            "debug": "\033[34m",     # Blue
            "info": "\033[32m",      # Green
            "warning": "\033[33m",   # Yellow
            "error": "\033[31m",     # Red
            "critical": "\033[1;31m"  # Bold Red
        }
        RESET = "\033[0m"

        # Create color style dict with pre-formatted strings
        level_styles = {
            level: f"{color}%s{RESET}" for level, color in COLORS.items()
        }

        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                level_styles=level_styles
            )
        )

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )

def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a logger instance."""
    logger = structlog.get_logger(name)
    
    # Bind thread-local context if it exists
    context = getattr(_thread_local, 'context', {})
    if context:
        logger = logger.bind(**context)
        
    return logger

def bind_logger_context(**kwargs) -> None:
    """Bind context to thread-local storage."""
    if not hasattr(_thread_local, 'context'):
        _thread_local.context = {}
    _thread_local.context.update(kwargs)

def clear_logger_context() -> None:
    """Clear thread-local context."""
    if hasattr(_thread_local, 'context'):
        del _thread_local.context