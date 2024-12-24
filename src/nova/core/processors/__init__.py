"""Core processors package."""

from .base import BaseProcessor
from .markdown import MarkdownProcessor
from .consolidate import ConsolidateProcessor
from .aggregate import AggregateProcessor

__all__ = [
    'BaseProcessor',
    'MarkdownProcessor',
    'ConsolidateProcessor',
    'AggregateProcessor'
]
