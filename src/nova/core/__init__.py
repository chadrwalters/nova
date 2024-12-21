"""Core module for Nova document processor."""

from .logging import setup_logger, get_logger
from .pipeline import Pipeline
from .config import NovaConfig
from .paths import NovaPaths
from .state import StateManager
from .errors import NovaError

__all__ = [
    'Pipeline', 
    'NovaConfig', 
    'NovaPaths', 
    'StateManager', 
    'NovaError',
    'setup_logger',
    'get_logger'
]