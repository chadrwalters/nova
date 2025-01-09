"""Metadata package for Nova document processor."""

from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.models.factory import MetadataFactory
from nova.context_processor.core.metadata.store import MetadataStore
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

__all__ = [
    "BaseMetadata",
    "MetadataFactory",
    "MetadataStore",
    "ArchiveMetadata",
    "AudioMetadata",
    "DocumentMetadata",
    "HTMLMetadata",
    "ImageMetadata",
    "MarkdownMetadata",
    "SpreadsheetMetadata",
    "TextMetadata",
    "VideoMetadata",
] 