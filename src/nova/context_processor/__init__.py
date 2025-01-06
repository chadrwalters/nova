"""Nova document processing library."""

__version__ = "3.0.0"

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.logging import print_summary
from nova.context_processor.core.nova import Nova
from nova.context_processor.handlers.archive import ArchiveHandler
from nova.context_processor.handlers.audio import AudioHandler
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.handlers.document import DocumentHandler
from nova.context_processor.handlers.image import ImageHandler
from nova.context_processor.handlers.registry import HandlerRegistry
from nova.context_processor.handlers.text import TextHandler

__all__ = [
    "Nova",
    "ConfigManager",
    "BaseHandler",
    "ImageHandler",
    "DocumentHandler",
    "AudioHandler",
    "ArchiveHandler",
    "TextHandler",
    "HandlerRegistry",
]
