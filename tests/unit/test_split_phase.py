"""Tests for split phase."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from nova.phases.split import SplitPhase
from nova.models.document import DocumentMetadata
from nova.models.links import LinkContext, LinkType

@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline."""
    pipeline = Mock()
    pipeline.state = {
        'split': {
            'successful_files': set(),
            'failed_files': set(),
            'section_stats': {}
        }
    }
    pipeline.config.processing_dir = Path("/test/processing")
    pipeline.config.output_dir = Path("/test/output")
    return pipeline

@pytest.fixture
def split_phase(mock_pipeline):
    """Create a split phase instance."""
    return SplitPhase(mock_pipeline)

@pytest.fixture
def sample_content():
    """Create sample content with summary and raw notes."""
    return """# Test Document

--==SUMMARY==--
Summary content.

--==RAW NOTES==--
Raw notes content."""

@pytest.fixture
def sample_metadata():
    """Create sample metadata."""
    return DocumentMetadata.from_file(
        file_path=Path("/test/path/test.md"),
        handler_name="test",
        handler_version="1.0"
    )

class TestSplitPhase:
    """Tests for SplitPhase class."""
    
    def test_init(self, mock_pipeline):
        """Test phase initialization."""
        phase = SplitPhase(mock_pipeline)
        assert phase.pipeline == mock_pipeline
        assert isinstance(phase.metadata_by_file, dict)
        assert isinstance(phase.attachments_by_main, dict)
        assert isinstance(phase.section_stats, dict)
        assert 'summary' in phase.section_stats
        assert 'raw_notes' in phase.section_stats
        assert 'attachments' in phase.section_stats
    
    def test_split_content(self, split_phase, sample_content):
        """Test splitting content into sections."""
        sections = split_phase._split_content(sample_content)
        assert 'summary' in sections
        assert 'raw_notes' in sections
        assert sections['summary'].strip() == "Summary content."
        assert sections['raw_notes'].strip() == "Raw notes content."
    
    def test_split_content_no_raw_notes(self, split_phase):
        """Test splitting content with no raw notes section."""
        content = """# Test Document

--==SUMMARY==--
Summary content."""
        sections = split_phase._split_content(content)
        assert 'summary' in sections
        assert sections['summary'].strip() == "Summary content."
        assert 'raw_notes' not in sections
    
    def test_update_links(self, split_phase, sample_metadata):
        """Test updating links in content."""
        content = "See [Target](target.md#section) for more info."
        source_file = "/test/path/source.md"
        
        updated_content = split_phase._update_links(
            content=content,
            source_file=source_file,
            metadata=sample_metadata
        )
        
        # Content should be unchanged
        assert updated_content == content
        
        # Link should be added to metadata
        assert len(sample_metadata.links.outgoing_links) == 1
        link = next(iter(sample_metadata.links.outgoing_links.values()))[0]
        assert link.source_file == source_file
        assert link.target_file == "target.md"
        assert link.target_section == "section"
        assert link.link_type == LinkType.OUTGOING
    
    def test_create_attachments_section(self, split_phase):
        """Test creating attachments section."""
        main_file = "test"
        split_phase.attachments_by_main[main_file] = {
            Path("/test/path/image.jpg"),
            Path("/test/path/doc.pdf")
        }
        
        content = split_phase._create_attachments_section(main_file)
        
        assert "# Attachments" in content
        assert "## JPG Files" in content
        assert "## PDF Files" in content
        assert "[image](image.jpg)" in content
        assert "[doc](doc.pdf)" in content
    
    def test_get_main_file_name(self, split_phase):
        """Test getting main file name from attachment path."""
        attachment_path = Path("/test/path/main_doc/attachment.pdf")
        main_file = split_phase._get_main_file_name(attachment_path)
        assert main_file == "main_doc"
    
    def test_update_section_stats(self, split_phase):
        """Test updating section statistics."""
        # Test regular section
        split_phase._update_section_stats('summary', 'processed')
        assert split_phase.section_stats['summary']['processed'] == 1
        
        # Test attachments section
        split_phase._update_section_stats('attachments', 'processed', 'pdf')
        assert split_phase.section_stats['attachments']['processed']['pdf'] == 1
    
    @pytest.mark.asyncio
    async def test_process_file_main(self, split_phase, sample_metadata, tmp_path):
        """Test processing a main file."""
        # Create test file in the parse phase output directory
        parse_dir = tmp_path / "phases" / "parse"
        parse_dir.mkdir(parents=True)
        file_path = parse_dir / "test.parsed.md"
        file_path.write_text("""# Test Document

--==SUMMARY==--
Summary content.

--==RAW NOTES==--
Raw notes content.""")
        
        # Set up output directory in the split phase directory
        split_dir = tmp_path / "phases" / "split"
        split_dir.mkdir(parents=True)
        
        # Update pipeline config
        split_phase.pipeline.config.processing_dir = tmp_path
        
        # Process file
        metadata = await split_phase.process_file(file_path, split_dir, sample_metadata)
        
        assert metadata.processed is True
        assert len(metadata.output_files) > 0
        assert split_phase.section_stats['summary']['processed'] == 1
        assert split_phase.section_stats['raw_notes']['processed'] == 1
    
    @pytest.mark.asyncio
    async def test_process_file_attachment(self, split_phase, sample_metadata, tmp_path):
        """Test processing an attachment file."""
        # Create test file
        main_dir = tmp_path / "main_doc"
        main_dir.mkdir()
        file_path = main_dir / "attachment.pdf"
        file_path.touch()
        
        # Process file
        metadata = await split_phase.process_file(file_path, tmp_path, sample_metadata)
        
        assert metadata.processed is True
        assert "main_doc" in split_phase.attachments_by_main
        assert file_path in split_phase.attachments_by_main["main_doc"]
        assert split_phase.section_stats['attachments']['processed']['pdf'] == 1 