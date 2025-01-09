"""Metadata types for different document types."""

from typing import Dict, List, Optional, Set

from pydantic import Field

from nova.context_processor.core.metadata.models.base import BaseMetadata


class TextMetadata(BaseMetadata):
    """Metadata for text files."""

    line_count: Optional[int] = Field(None, description="Number of lines")
    word_count: Optional[int] = Field(None, description="Number of words")
    char_count: Optional[int] = Field(None, description="Number of characters")
    encoding: Optional[str] = Field(None, description="Text encoding")


class DocumentMetadata(BaseMetadata):
    """Metadata for document files."""

    page_count: Optional[int] = Field(None, description="Number of pages")
    word_count: Optional[int] = Field(None, description="Number of words")
    author: Optional[str] = Field(None, description="Document author")
    keywords: Set[str] = Field(default_factory=set, description="Document keywords")


class ImageMetadata(BaseMetadata):
    """Metadata for image files."""

    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    format: Optional[str] = Field(None, description="Image format")
    color_space: Optional[str] = Field(None, description="Color space")
    dpi: Optional[int] = Field(None, description="Dots per inch")
    has_alpha: Optional[bool] = Field(None, description="Whether image has alpha channel")


class VideoMetadata(BaseMetadata):
    """Metadata for video files."""

    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    fps: Optional[float] = Field(None, description="Frames per second")
    codec: Optional[str] = Field(None, description="Video codec")
    audio_codec: Optional[str] = Field(None, description="Audio codec")
    has_audio: Optional[bool] = Field(None, description="Whether video has audio")


class AudioMetadata(BaseMetadata):
    """Metadata for audio files."""

    duration: Optional[float] = Field(None, description="Duration in seconds")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")
    channels: Optional[int] = Field(None, description="Number of audio channels")
    codec: Optional[str] = Field(None, description="Audio codec")
    bit_rate: Optional[int] = Field(None, description="Bit rate in kbps")
    bit_depth: Optional[int] = Field(None, description="Bit depth")


class HTMLMetadata(BaseMetadata):
    """Metadata for HTML files."""

    charset: Optional[str] = Field(None, description="Character encoding")
    links: Set[str] = Field(default_factory=set, description="External links")
    images: Set[str] = Field(default_factory=set, description="Image references")
    scripts: Set[str] = Field(default_factory=set, description="Script references")
    styles: Set[str] = Field(default_factory=set, description="Style references")


class MarkdownMetadata(BaseMetadata):
    """Metadata for Markdown files."""

    line_count: Optional[int] = Field(None, description="Number of lines")
    word_count: Optional[int] = Field(None, description="Number of words")
    char_count: Optional[int] = Field(None, description="Number of characters")
    has_frontmatter: Optional[bool] = Field(None, description="Whether file has frontmatter")
    has_links: Optional[bool] = Field(None, description="Whether file has links")
    has_images: Optional[bool] = Field(None, description="Whether file has images")
    has_code_blocks: Optional[bool] = Field(None, description="Whether file has code blocks")
    has_tables: Optional[bool] = Field(None, description="Whether file has tables")
    has_math: Optional[bool] = Field(None, description="Whether file has math")
    has_html: Optional[bool] = Field(None, description="Whether file has HTML")
    links: Set[str] = Field(default_factory=set, description="External links")
    images: Set[str] = Field(default_factory=set, description="Image references")
    headings: Set[str] = Field(default_factory=set, description="Heading text")
    code_blocks: Set[str] = Field(default_factory=set, description="Code block languages")


class SpreadsheetMetadata(BaseMetadata):
    """Metadata for spreadsheet files."""

    sheet_count: Optional[int] = Field(None, description="Number of sheets")
    total_rows: Optional[int] = Field(None, description="Total number of rows")
    total_columns: Optional[int] = Field(None, description="Total number of columns")
    has_formulas: Optional[bool] = Field(None, description="Whether file contains formulas")
    has_macros: Optional[bool] = Field(None, description="Whether file contains macros")


class ArchiveMetadata(BaseMetadata):
    """Metadata for archive files."""

    format: Optional[str] = Field(None, description="Archive format")
    compression: Optional[str] = Field(None, description="Compression method")
    total_files: Optional[int] = Field(None, description="Total number of files")
    total_size: Optional[int] = Field(None, description="Total uncompressed size")
    files: List[Dict[str, str]] = Field(default_factory=list, description="List of files in archive") 