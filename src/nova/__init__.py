"""Nova document processor package."""

from .core.logging import setup_logger, get_logger
from .core.pipeline import Pipeline
from .core.config import NovaConfig
from .core.paths import NovaPaths
from .core.state import StateManager
from .core.errors import NovaError

__version__ = "0.1.0"

__all__ = [
    'Pipeline',
    'NovaConfig',
    'NovaPaths',
    'StateManager',
    'NovaError',
    'setup_logger',
    'get_logger'
] 