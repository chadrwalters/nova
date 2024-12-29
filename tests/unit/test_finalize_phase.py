"""Tests for finalize phase."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from nova.phases.finalize import FinalizePhase
from nova.models.document import DocumentMetadata
from nova.models.links import LinkContext, LinkType, LinkMap

@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline."""
    pipeline = Mock()
    pipeline.state = {
        'finalize': {
            'successful_files': set(),
            'failed_files': set()
        }
    }
    pipeline.config.output_dir = Path("/test/output")
    pipeline.config.processing_dir = Path("/test/processing")
    return pipeline

@pytest.fixture
def finalize_phase(mock_pipeline):
    """Create a finalize phase instance."""
    return FinalizePhase(mock_pipeline)

@pytest.fixture
def sample_metadata():
    """Create sample metadata."""
    metadata = DocumentMetadata.from_file(
        file_path=Path("/test/path/test.md"),
        handler_name="test",
        handler_version="1.0"
    )
    # Create a link map with test data
    link_map = LinkMap()
    link_map.add_link(
        LinkContext(
            source_file="/test/path/source.md",
            target_file="target.md",
            target_section="section",
            link_type=LinkType.OUTGOING
        )
    )
    metadata.links = link_map
    return metadata

class TestFinalizePhase:
    """Tests for FinalizePhase class."""
    
    def test_init(self, mock_pipeline):
        """Test phase initialization."""
        phase = FinalizePhase(mock_pipeline)
        assert phase.pipeline == mock_pipeline
        assert phase.link_map is None
    
    def test_validate_links(self, finalize_phase, sample_metadata, tmp_path):
        """Test link validation."""
        # Create a test file that the link points to
        target_file = tmp_path / "target.md"
        target_file.write_text("""# Test
<a id="section"></a>
Test content""")
        
        # Update link target to point to the test file
        link = next(iter(sample_metadata.links.outgoing_links.values()))[0]
        link.target_file = str(target_file)
        
        # Validate links
        errors = finalize_phase._validate_links(sample_metadata)
        assert not errors
    
    def test_validate_links_broken(self, finalize_phase, sample_metadata, tmp_path):
        """Test validation of broken links."""
        # Create a link to a non-existent file in the temporary directory
        nonexistent_file = tmp_path / "nonexistent.md"
        link = LinkContext(
            source_file=str(sample_metadata.file_path),
            target_file=str(nonexistent_file),
            target_section="section",
            link_type=LinkType.OUTGOING
        )
        sample_metadata.links.add_link(link)
        
        # Set up link map
        finalize_phase.link_map = sample_metadata.links
        
        # Validate links
        errors = finalize_phase._validate_links(sample_metadata)
        assert len(errors) > 0
        assert "does not exist" in errors[0]
    
    def test_section_exists(self, finalize_phase, tmp_path):
        """Test section existence check."""
        # Create a test file with a section
        test_file = tmp_path / "test.md"
        test_file.write_text("""# Test
<a id="section"></a>
Test content""")
        
        assert finalize_phase._section_exists(test_file, "section")
        assert not finalize_phase._section_exists(test_file, "nonexistent")
    
    @pytest.mark.asyncio
    async def test_process_file(self, finalize_phase, sample_metadata, tmp_path):
        """Test processing a file."""
        # Create test file
        file_path = tmp_path / "test.md"
        file_path.write_text("""# Test Document
        
        This is a test document with a [link](target.md#section).""")
        
        # Set up directories
        split_dir = tmp_path / "phases" / "split"
        split_dir.mkdir(parents=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Copy test file to split directory
        split_file = split_dir / file_path.name
        split_file.write_text(file_path.read_text())
        
        finalize_phase.pipeline.config.processing_dir = tmp_path
        finalize_phase.pipeline.config.output_dir = output_dir
        
        # Initialize link map
        finalize_phase.link_map = sample_metadata.links
        
        # Process file
        metadata = await finalize_phase.process_file(file_path, tmp_path, sample_metadata)
        
        assert metadata is not None
        assert metadata.processed is True
        assert len(metadata.output_files) > 0
    
    @pytest.mark.asyncio
    async def test_process_file_no_links(self, finalize_phase, sample_metadata, tmp_path):
        """Test processing a file with no links."""
        # Create test file
        file_path = tmp_path / "test.md"
        file_path.write_text("""# Test Document
        
        This is a test document with no links.""")
        
        # Set up directories
        split_dir = tmp_path / "phases" / "split"
        split_dir.mkdir(parents=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Copy test file to split directory
        split_file = split_dir / file_path.name
        split_file.write_text(file_path.read_text())
        
        finalize_phase.pipeline.config.processing_dir = tmp_path
        finalize_phase.pipeline.config.output_dir = output_dir
        
        # Initialize empty link map
        finalize_phase.link_map = LinkMap()
        
        # Process file
        metadata = await finalize_phase.process_file(file_path, tmp_path, sample_metadata)
        
        assert metadata is not None
        assert metadata.processed is True
        assert len(metadata.output_files) > 0
    
    def test_finalize(self, finalize_phase, sample_metadata):
        """Test finalize method."""
        # Set up link map
        finalize_phase.link_map = sample_metadata.links
        
        # Add some test data to pipeline state
        finalize_phase.pipeline.state['finalize'] = {
            'failed_files': set(['failed.md']),
            'successful_files': set(['success.md'])
        }
        
        # Call finalize
        finalize_phase.finalize()
        
        # Check that link validation was performed
        assert 'link_validation' in finalize_phase.pipeline.state['finalize']
        stats = finalize_phase.pipeline.state['finalize']['link_validation']
        assert 'total_links' in stats
        assert 'broken_links' in stats
        assert 'repaired_links' in stats 