"""Nova document processing library."""

__version__ = "3.0.0"

from nova.config.manager import ConfigManager
from nova.core.logging import print_summary
from nova.core.nova import Nova
from nova.handlers.archive import ArchiveHandler
from nova.handlers.audio import AudioHandler
from nova.handlers.base import BaseHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.image import ImageHandler
from nova.handlers.registry import HandlerRegistry
from nova.handlers.text import TextHandler

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
