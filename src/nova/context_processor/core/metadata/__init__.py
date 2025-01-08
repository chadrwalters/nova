"""Metadata package for Nova document processor."""

from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.models.factory import MetadataFactory
from nova.context_processor.core.metadata.models.types import (
    ArchiveMetadata,
    AudioMetadata,
    DocumentMetadata,
    HTMLMetadata,
    ImageMetadata,
    MarkdownMetadata,
    SpreadsheetMetadata,
    TextMetadata,
    VideoMetadata,
)
from nova.context_processor.core.metadata.store.manager import MetadataStore

__all__ = [
    "ArchiveMetadata",
    "AudioMetadata",
    "BaseMetadata",
    "DocumentMetadata",
    "HTMLMetadata",
    "ImageMetadata",
    "MarkdownMetadata",
    "SpreadsheetMetadata",
    "TextMetadata",
    "VideoMetadata",
    "MetadataFactory",
    "MetadataStore",
] 