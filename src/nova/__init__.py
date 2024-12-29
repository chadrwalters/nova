"""Nova document processing library."""

__version__ = "0.1.0"

from nova.core.nova import Nova
from nova.config.manager import ConfigManager
from nova.handlers.base import BaseHandler
from nova.handlers.image import ImageHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.audio import AudioHandler
from nova.handlers.archive import ArchiveHandler
from nova.handlers.text import TextHandler
from nova.handlers.registry import HandlerRegistry
from nova.core.logging import print_summary

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