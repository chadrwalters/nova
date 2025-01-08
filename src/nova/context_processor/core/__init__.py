"""Core package for Nova document processor."""

from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.nova import Nova

__all__ = ["Nova", "NovaConfig"]
