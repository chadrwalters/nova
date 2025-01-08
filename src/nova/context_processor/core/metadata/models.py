"""Metadata models package."""

# All metadata models are now defined in models/base.py and models/types.py
from .models.base import (
    BaseMetadata,
    MetadataVersion,
)

from .models.types import (
    TextMetadata,
    DocumentMetadata,
    ImageMetadata,
    VideoMetadata,
    AudioMetadata,
    SpreadsheetMetadata,
    ArchiveMetadata,
    HTMLMetadata,
    MarkdownMetadata,
)

__all__ = [
    'BaseMetadata',
    'MetadataVersion',
    'TextMetadata',
    'DocumentMetadata',
    'ImageMetadata',
    'VideoMetadata',
    'AudioMetadata',
    'SpreadsheetMetadata',
    'ArchiveMetadata',
    'HTMLMetadata',
    'MarkdownMetadata',
] 