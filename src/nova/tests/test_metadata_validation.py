"""Tests for metadata validation system."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from nova.context_processor.core.metadata.models.base import BaseMetadata, MetadataVersion
from nova.context_processor.core.metadata.models.types import (
    ImageMetadata,
    DocumentMetadata,
    MarkdownMetadata,
    ArchiveMetadata,
)
from nova.context_processor.core.metadata.validation import MetadataValidator
from nova.context_processor.core.metadata.store.manager import MetadataStore


@pytest.fixture
def metadata_store():
    """Create a mock metadata store."""
    return Mock(spec=MetadataStore)


@pytest.fixture
def validator(metadata_store):
    """Create a metadata validator instance."""
    return MetadataValidator(metadata_store)


def test_validate_schema_image_metadata(validator):
    """Test validation of image metadata."""
    # Valid metadata
    metadata = ImageMetadata(
        file_path=Path("test.jpg"),
        file_type="image/jpeg",
        file_size=1000,
        width=100,
        height=200,
        dpi=(72, 72),
        mode="RGB",
        has_alpha=False,
        current_version=MetadataVersion(major=1, minor=0),
    )
    errors = validator.validate_schema(metadata)
    assert not errors

    # Invalid width
    metadata.width = -100
    errors = validator.validate_schema(metadata)
    assert "Invalid image width" in errors

    # Invalid height
    metadata.width = 100
    metadata.height = -200
    errors = validator.validate_schema(metadata)
    assert "Invalid image height" in errors

    # Invalid DPI
    metadata.height = 200
    metadata.dpi = (-72, 72)
    errors = validator.validate_schema(metadata)
    assert "Invalid DPI values" in errors

    # Invalid alpha channel
    metadata.dpi = (72, 72)
    metadata.has_alpha = True
    metadata.mode = "RGB"
    errors = validator.validate_schema(metadata)
    assert "Alpha channel indicated but mode is not RGBA/LA" in errors


def test_validate_schema_document_metadata(validator):
    """Test validation of document metadata."""
    # Valid metadata
    metadata = DocumentMetadata(
        file_path=Path("test.pdf"),
        file_type="application/pdf",
        file_size=1000,
        page_count=10,
        word_count=1000,
        sections=[{"title": "Section 1", "content": "Content 1"}],
        current_version=MetadataVersion(major=1, minor=0),
    )
    errors = validator.validate_schema(metadata)
    assert not errors

    # Invalid page count
    metadata.page_count = -1
    errors = validator.validate_schema(metadata)
    assert "Invalid page count" in errors

    # Invalid word count
    metadata.page_count = 10
    metadata.word_count = -100
    errors = validator.validate_schema(metadata)
    assert "Invalid word count" in errors

    # Invalid section structure
    metadata.word_count = 1000
    metadata.sections = [{"content": "Missing title"}]
    errors = validator.validate_schema(metadata)
    assert "Missing section title" in errors


def test_validate_schema_markdown_metadata(validator):
    """Test validation of markdown metadata."""
    # Valid metadata
    metadata = MarkdownMetadata(
        file_path=Path("test.md"),
        file_type="text/markdown",
        file_size=1000,
        headings=[
            {"level": 1, "text": "Title"},
            {"level": 2, "text": "Subtitle"},
        ],
        links=[{"text": "Link", "url": "https://example.com"}],
        embedded_files=[],
        current_version=MetadataVersion(major=1, minor=0),
    )
    errors = validator.validate_schema(metadata)
    assert not errors

    # Invalid heading structure
    metadata.headings = [{"level": 1}]
    errors = validator.validate_schema(metadata)
    assert "Invalid heading structure" in errors

    # Invalid heading level progression
    metadata.headings = [
        {"level": 1, "text": "Title"},
        {"level": 3, "text": "Invalid level"},
    ]
    errors = validator.validate_schema(metadata)
    assert "Invalid heading level progression" in errors

    # Invalid link structure
    metadata.headings = [{"level": 1, "text": "Title"}]
    metadata.links = [{"text": "Missing URL"}]
    errors = validator.validate_schema(metadata)
    assert "Invalid link structure" in errors


def test_validate_schema_archive_metadata(validator):
    """Test validation of archive metadata."""
    # Valid metadata
    metadata = ArchiveMetadata(
        file_path=Path("test.zip"),
        file_type="application/zip",
        file_size=1000,
        file_count=2,
        total_size=2000,
        contents=[
            {"path": "file1.txt", "size": 1000},
            {"path": "file2.txt", "size": 1000},
        ],
        current_version=MetadataVersion(major=1, minor=0),
    )
    errors = validator.validate_schema(metadata)
    assert not errors

    # Invalid file count
    metadata.file_count = -1
    errors = validator.validate_schema(metadata)
    assert "Invalid file count" in errors

    # File count mismatch
    metadata.file_count = 3
    errors = validator.validate_schema(metadata)
    assert "File count mismatch with contents" in errors

    # Invalid total size
    metadata.file_count = 2
    metadata.total_size = 500
    errors = validator.validate_schema(metadata)
    assert "Total uncompressed size smaller than compressed size" in errors

    # Invalid content structure
    metadata.total_size = 2000
    metadata.contents = [{"path": "file1.txt"}]
    errors = validator.validate_schema(metadata)
    assert "Invalid archive content structure" in errors


def test_validate_cross_phase(validator, metadata_store):
    """Test validation across processing phases."""
    file_path = Path("test.md")
    phases = ["parse", "process", "validate"]

    # Set up mock metadata for different phases
    base_metadata = MarkdownMetadata(
        file_path=file_path,
        file_type="text/markdown",
        file_size=1000,
        current_version=MetadataVersion(major=1, minor=0),
    )
    process_metadata = MarkdownMetadata(
        file_path=file_path,
        file_type="text/markdown",
        file_size=1000,
        current_version=MetadataVersion(major=1, minor=1),
    )
    validate_metadata = MarkdownMetadata(
        file_path=file_path,
        file_type="text/markdown",
        file_size=1000,
        current_version=MetadataVersion(major=2, minor=0),
    )

    metadata_store.get.side_effect = lambda p, phase: {
        "parse": base_metadata,
        "process": process_metadata,
        "validate": validate_metadata,
    }.get(phase)

    # Test valid version progression
    errors = validator.validate_cross_phase(file_path, phases)
    assert not errors

    # Test invalid version progression (major version decrease)
    validate_metadata.current_version = MetadataVersion(major=0, minor=0)
    errors = validator.validate_cross_phase(file_path, phases)
    assert any("major version decreased" in error for error in errors)

    # Test invalid version progression (minor version decrease)
    validate_metadata.current_version = MetadataVersion(major=1, minor=0)
    errors = validator.validate_cross_phase(file_path, phases)
    assert any("minor version decreased" in error for error in errors)

    # Test file path mismatch
    process_metadata.file_path = Path("different.md")
    errors = validator.validate_cross_phase(file_path, phases)
    assert "File path mismatch in process" in errors


def test_validate_related_metadata(validator, metadata_store):
    """Test validation of related metadata."""
    # Test markdown with embedded files
    markdown_metadata = MarkdownMetadata(
        file_path=Path("test.md"),
        file_type="text/markdown",
        file_size=1000,
        embedded_files=[Path("image.jpg")],
        current_version=MetadataVersion(major=1, minor=0),
    )

    # Mock missing embedded file metadata
    metadata_store.get.return_value = None
    errors = validator.validate_related_metadata(markdown_metadata)
    assert "Missing metadata for embedded file: image.jpg" in errors

    # Test archive with contents
    archive_metadata = ArchiveMetadata(
        file_path=Path("test.zip"),
        file_type="application/zip",
        file_size=1000,
        contents=[{"path": "file.txt", "size": 100}],
        current_version=MetadataVersion(major=1, minor=0),
    )

    # Mock missing archive content metadata
    metadata_store.get.return_value = None
    errors = validator.validate_related_metadata(archive_metadata)
    assert "Missing metadata for archive content: file.txt" in errors 