"""Logging configuration for Nova."""
import logging
import sys
from collections import defaultdict
from typing import Any, Dict, Optional, Set, Union

import structlog
import structlog.processors
import structlog.stdlib
import structlog.dev
import structlog.typing
from rich.console import Console
from structlog.types import EventDict, Processor

# Configure standard logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Rich console for pretty output
console = Console()

# Track duplicate messages
_duplicate_messages: Dict[str, Set[str]] = defaultdict(set)

def add_timestamp(
    logger: str, name: str, event_dict: EventDict
) -> EventDict:
    """Add timestamp in a standardized format.
    
    Args:
        logger: Logger instance name
        name: Event name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    # We'll let structlog handle the timestamp
    return event_dict

def add_log_level(
    logger: str, level_name: str, event_dict: EventDict
) -> EventDict:
    """Add log level with consistent formatting.
    
    Args:
        logger: Logger instance name
        level_name: Log level name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    event_dict["level"] = level_name.lower()
    return event_dict

def format_exc_info(
    logger: str, name: str, event_dict: EventDict
) -> EventDict:
    """Format exception info if present.
    
    Args:
        logger: Logger instance name
        name: Event name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    if "exc_info" in event_dict and event_dict["exc_info"]:
        event_dict["error"] = str(event_dict["exc_info"])
    return event_dict

def format_stack_info(
    logger: str, name: str, event_dict: EventDict
) -> EventDict:
    """Format stack info if present.
    
    Args:
        logger: Logger instance name
        name: Event name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    if "stack_info" in event_dict and event_dict["stack_info"]:
        event_dict["stack"] = event_dict["stack_info"]
    return event_dict

def clean_message(
    logger: str, name: str, event_dict: EventDict
) -> EventDict:
    """Clean and standardize message format.
    
    Args:
        logger: Logger instance name
        name: Event name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict

def deduplicate_messages(
    logger: str, level: str, event_dict: EventDict
) -> Optional[EventDict]:
    """Deduplicate repeated log messages.
    
    Args:
        logger: Logger instance name
        level: Log level
        event_dict: Event dictionary

    Returns:
        Modified event dictionary or None if message is duplicate
    """
    message = event_dict.get("message", "")
    if not message:
        return event_dict
        
    # Create a key that combines logger, level and message type
    msg_type = message.split(":")[0] if ":" in message else message
    key = f"{logger}:{level}:{msg_type}"
    
    # For attachment warnings, extract just the filename
    if "Attachment file not found" in message:
        filepath = message.split(": ")[-1]
        filename = filepath.split("/")[-1]
        if filename not in _duplicate_messages[key]:
            _duplicate_messages[key].add(filename)
            # Simplify the message to show just filename
            event_dict["message"] = f"Attachment file not found: {filename}"
            return event_dict
        return None
    
    # For other messages, check if exact message was logged
    if message not in _duplicate_messages[key]:
        _duplicate_messages[key].add(message)
        return event_dict
        
    return None

def setup_logging(level: str = "INFO", pretty: bool = True) -> None:
    """Set up logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        pretty: Whether to use pretty formatting for console output
    """
    # Set log level
    logging.getLogger().setLevel(level)
    
    # Common processors
    processors_list: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        add_log_level,
        format_exc_info,
        format_stack_info,
        clean_message,
        deduplicate_messages,
        structlog.processors.StackInfoRenderer(),
    ]

    if pretty:
        # Add pretty printing for console output
        processors_list.extend([
            structlog.dev.ConsoleRenderer(
                colors=True,
                level_styles={
                    "debug": "bright_blue",
                    "info": "bright_green", 
                    "warning": "yellow",
                    "error": "red",
                    "critical": "red bold",
                },
                pad_event=0,
            ),
        ])
    else:
        # Use JSON formatting for machine parsing
        processors_list.extend([
            structlog.processors.JSONRenderer()
        ])

    # Configure structlog with type-safe configuration
    # Note: We use getattr to avoid mypy error with configure
    configure = getattr(structlog, "configure")
    configure(
        processors=processors_list,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a logger instance with standardized configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name) 