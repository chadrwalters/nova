"""Tests for metadata models."""

import pytest
from pathlib import Path
from nova.core.metadata import FileMetadata
from nova.models.links import LinkContext, LinkType

@pytest.fixture
def sample_file_path():
    """Create a sample file path."""
    return Path("/test/path/file.txt")

@pytest.fixture
def sample_metadata(sample_file_path):
    """Create a sample metadata instance."""
    return FileMetadata(sample_file_path)

@pytest.fixture
def sample_link():
    """Create a sample link context."""
    return LinkContext(
        source_file="/test/path/source.md",
        target_file="/test/path/target.md",
        target_section="section-1",
        link_type=LinkType.OUTGOING,
        context="Sample context",
        title="Sample Link"
    )

class TestFileMetadata:
    """Tests for FileMetadata class."""
    
    def test_init(self, sample_file_path):
        """Test metadata initialization."""
        metadata = FileMetadata(sample_file_path)
        assert metadata.file_path == sample_file_path
        assert metadata.processed is False
        assert metadata.unchanged is False
        assert metadata.reprocessed is False
        assert isinstance(metadata.output_files, set)
        assert isinstance(metadata.errors, dict)
        assert isinstance(metadata.metadata, dict)
        assert metadata.title is None
        assert metadata.has_errors is False
        assert isinstance(metadata.links, list)
    
    def test_add_error(self, sample_metadata):
        """Test adding an error."""
        sample_metadata.add_error("test_handler", "test error")
        assert "test_handler" in sample_metadata.errors
        assert sample_metadata.errors["test_handler"] == "test error"
        assert sample_metadata.has_errors is True
    
    def test_add_output_file(self, sample_metadata):
        """Test adding an output file."""
        output_file = Path("/test/path/output.txt")
        sample_metadata.add_output_file(output_file)
        assert output_file in sample_metadata.output_files
    
    def test_add_link(self, sample_metadata, sample_link):
        """Test adding a link."""
        sample_metadata.add_link(sample_link)
        assert len(sample_metadata.links) == 1
        assert sample_metadata.links[0] == sample_link
    
    def test_get_outgoing_links(self, sample_metadata, sample_link):
        """Test getting outgoing links."""
        # Add a link where this file is the source
        outgoing_link = LinkContext(
            source_file=str(sample_metadata.file_path),
            target_file="/test/path/target.md"
        )
        sample_metadata.add_link(outgoing_link)
        
        # Add a link where this file is the target
        incoming_link = LinkContext(
            source_file="/test/path/other.md",
            target_file=str(sample_metadata.file_path)
        )
        sample_metadata.add_link(incoming_link)
        
        outgoing_links = sample_metadata.get_outgoing_links()
        assert len(outgoing_links) == 1
        assert outgoing_links[0] == outgoing_link
    
    def test_get_incoming_links(self, sample_metadata, sample_link):
        """Test getting incoming links."""
        # Add a link where this file is the source
        outgoing_link = LinkContext(
            source_file=str(sample_metadata.file_path),
            target_file="/test/path/target.md"
        )
        sample_metadata.add_link(outgoing_link)
        
        # Add a link where this file is the target
        incoming_link = LinkContext(
            source_file="/test/path/other.md",
            target_file=str(sample_metadata.file_path)
        )
        sample_metadata.add_link(incoming_link)
        
        incoming_links = sample_metadata.get_incoming_links()
        assert len(incoming_links) == 1
        assert incoming_links[0] == incoming_link
    
    def test_from_file(self, sample_file_path):
        """Test creating metadata from a file."""
        metadata = FileMetadata.from_file(
            sample_file_path,
            "test_handler",
            "1.0"
        )
        assert metadata.file_path == sample_file_path
        assert metadata.title == sample_file_path.stem
        assert metadata.metadata["file_name"] == sample_file_path.name
        assert metadata.metadata["file_path"] == str(sample_file_path)
        assert metadata.metadata["file_type"] == sample_file_path.suffix[1:]
        assert metadata.metadata["handler_name"] == "test_handler"
        assert metadata.metadata["handler_version"] == "1.0" 