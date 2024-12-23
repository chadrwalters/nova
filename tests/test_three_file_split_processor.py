"""Tests for the ThreeFileSplitProcessor class."""

import pytest
import time
import concurrent.futures
from pathlib import Path
from nova.core.config import ProcessorConfig, NovaConfig, PathsConfig
from nova.core.errors import ProcessingError
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

@pytest.fixture
def nova_config(tmp_path):
    """Create a test Nova configuration."""
    paths = PathsConfig(
        base_dir=tmp_path,
        input_dir=tmp_path / 'input',
        output_dir=tmp_path / 'output',
        processing_dir=tmp_path / 'processing',
        temp_dir=tmp_path / 'temp',
        state_dir=tmp_path / 'state',
        phase_dirs={
            'markdown_parse': tmp_path / 'phases/markdown_parse',
            'markdown_consolidate': tmp_path / 'phases/markdown_consolidate',
            'markdown_aggregate': tmp_path / 'phases/markdown_aggregate',
            'markdown_split': tmp_path / 'phases/markdown_split'
        },
        image_dirs={
            'original': tmp_path / 'images/original',
            'processed': tmp_path / 'images/processed',
            'metadata': tmp_path / 'images/metadata',
            'cache': tmp_path / 'images/cache'
        },
        office_dirs={
            'assets': tmp_path / 'office/assets',
            'temp': tmp_path / 'office/temp'
        }
    )
    
    # Create all directories
    paths.base_dir.mkdir(exist_ok=True)
    paths.input_dir.mkdir(exist_ok=True)
    paths.output_dir.mkdir(exist_ok=True)
    paths.processing_dir.mkdir(exist_ok=True)
    paths.temp_dir.mkdir(exist_ok=True)
    paths.state_dir.mkdir(exist_ok=True)
    
    for phase_dir in paths.phase_dirs.values():
        phase_dir.mkdir(parents=True, exist_ok=True)
    
    for image_dir in paths.image_dirs.values():
        image_dir.mkdir(parents=True, exist_ok=True)
    
    for office_dir in paths.office_dirs.values():
        office_dir.mkdir(parents=True, exist_ok=True)
    
    return NovaConfig(paths=paths)

@pytest.fixture
def processor_config():
    """Create a test processor configuration."""
    return ProcessorConfig(
        enabled=True,
        options={
            'components': {
                'three_file_split_processor': {
                    'config': {
                        'output_files': {
                            'summary': 'summary.md',
                            'raw_notes': 'raw_notes.md',
                            'attachments': 'attachments.md'
                        },
                        'section_markers': {
                            'summary': '--==SUMMARY==--',
                            'raw_notes': '--==RAW_NOTES==--',
                            'attachments': '--==ATTACHMENTS==--'
                        },
                        'attachment_markers': {
                            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                            'end': '--==ATTACHMENT_BLOCK_END==--'
                        },
                        'content_type_rules': {
                            'summary': [
                                'Contains high-level overviews',
                                'Contains key insights and decisions',
                                'Contains structured content'
                            ],
                            'raw_notes': [
                                'Contains detailed notes and logs',
                                'Contains chronological entries',
                                'Contains unstructured content'
                            ],
                            'attachments': [
                                'Contains file references',
                                'Contains embedded content',
                                'Contains metadata'
                            ]
                        }
                    }
                }
            }
        }
    )

@pytest.fixture
def processor(processor_config, nova_config):
    """Create a ThreeFileSplitProcessor instance for testing."""
    return ThreeFileSplitProcessor(processor_config, nova_config)

@pytest.fixture
def setup_files(tmp_path):
    """Set up test files."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(exist_ok=True)

    # Create test files
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--
# Test Document
This is a summary section.
[Link to attachment](test.txt)

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.
See [another attachment](data.csv)

--==ATTACHMENTS==--
--==ATTACHMENT_BLOCK: test.txt==--
This is a test file content.
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: data.csv==--
col1,col2
1,2
3,4
--==ATTACHMENT_BLOCK_END==--
""")

    return input_dir, output_dir

def test_setup(processor, tmp_path):
    """Test processor setup."""
    # Setup should have already been called by constructor
    assert processor.stats == {
        'total_content_size': 0,
        'summary_size': 0,
        'raw_notes_size': 0,
        'attachments_size': 0,
        'headers_processed': 0,
        'attachments_processed': 0
    }
    
    # Output directory should exist
    assert Path(processor.nova_config.paths.output_dir).exists()

def test_process_files(processor, setup_files):
    """Test processing input files."""
    input_dir, output_dir = setup_files
    input_files = list(input_dir.glob('*.md'))
    
    # Process files
    output_files = processor.process(input_files[0], output_dir)
    
    # Check output files were created
    assert len(output_files) == 3
    assert any(f.name == 'summary.md' for f in output_files)
    assert any(f.name == 'raw_notes.md' for f in output_files)
    assert any(f.name == 'attachments.md' for f in output_files)

def test_empty_input(processor, tmp_path):
    """Test processing with no input files."""
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with pytest.raises(ProcessingError, match="No input files provided"):
        processor.process(None, output_dir)

def test_missing_sections(processor, tmp_path):
    """Test processing file with missing sections."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create test file with missing sections
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--
# Test Document
This is a summary section.

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.
""")

    # Process should succeed since sections are optional
    output_files = processor.process(test_file, output_dir)
    assert len(output_files) == 3
    
    # Verify content in output files
    summary_file = output_dir / 'summary.md'
    raw_notes_file = output_dir / 'raw_notes.md'
    attachments_file = output_dir / 'attachments.md'
    
    assert summary_file.exists()
    assert raw_notes_file.exists()
    assert attachments_file.exists()
    
    # Summary and raw notes should have content
    assert summary_file.read_text().strip() != ""
    assert raw_notes_file.read_text().strip() != ""
    
    # Attachments file should be empty except for header and navigation
    attachments_content = attachments_file.read_text().strip()
    assert "# Attachments" in attachments_content
    assert len(attachments_content.split('\n')) <= 5  # Header + blank + nav + 2 links

def test_invalid_markers(processor, tmp_path):
    """Test processing file with invalid markers."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create test file with invalid markers
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==INVALID==--
# Test Document
This is an invalid section.

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.

--==ATTACHMENTS==--
No attachments.
""")

    with pytest.raises(ProcessingError, match="Invalid section marker: INVALID"):
        processor.process(test_file, output_dir)

def test_empty_sections(processor, tmp_path):
    """Test handling of empty content sections."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create test file with empty sections
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--

--==RAW_NOTES==--

--==ATTACHMENTS==--
""")

    with pytest.raises(ProcessingError, match="No content found in any section"):
        processor.process(test_file, output_dir)

def test_basic_split(processor, tmp_path):
    """Test basic split functionality."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create test file with basic split
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--
# Test Document
This is a summary section.

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.

--==ATTACHMENTS==--
No attachments.
""")

    # Process should succeed
    output_files = processor.process(test_file, output_dir)
    assert len(output_files) == 3

    # Verify content of each file
    summary_file = output_dir / 'summary.md'
    assert summary_file.exists()
    assert "# Test Document" in summary_file.read_text()

    raw_notes_file = output_dir / 'raw_notes.md'
    assert raw_notes_file.exists()
    assert "## Raw Notes" in raw_notes_file.read_text()

    attachments_file = output_dir / 'attachments.md'
    assert attachments_file.exists()
    assert "No attachments" in attachments_file.read_text()

def test_summary_content(processor, setup_files):
    """Test summary file content."""
    input_dir, output_dir = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_files = processor.process(input_files[0], output_dir)
    
    # Find summary file
    summary_file = next(f for f in output_files if f.name == 'summary.md')
    content = summary_file.read_text()
    
    # Check content
    assert '# Summary' in content
    assert 'Test Document' in content
    assert 'This is a summary section' in content
    assert 'Navigation:' in content
    assert '[Raw Notes]' in content
    assert '[Attachments]' in content

def test_raw_notes_content(processor, setup_files):
    """Test raw notes file content."""
    input_dir, output_dir = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_files = processor.process(input_files[0], output_dir)
    
    # Find raw notes file
    raw_notes_file = next(f for f in output_files if f.name == 'raw_notes.md')
    content = raw_notes_file.read_text()
    
    # Check content
    assert '# Raw Notes' in content
    assert 'These are some raw notes' in content
    assert 'Navigation:' in content
    assert '[Summary]' in content
    assert '[Attachments]' in content

def test_attachments_content(processor, setup_files):
    """Test attachments file content."""
    input_dir, output_dir = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_files = processor.process(input_files[0], output_dir)
    
    # Find attachments file
    attachments_file = next(f for f in output_files if f.name == 'attachments.md')
    content = attachments_file.read_text()
    
    # Check content
    assert '# Attachments' in content
    assert '--==ATTACHMENT_BLOCK: test.txt==--' in content
    assert '--==ATTACHMENT_BLOCK: data.csv==--' in content
    assert 'This is a test file content' in content
    assert 'col1,col2' in content
    assert 'Navigation:' in content
    assert '[Summary]' in content
    assert '[Raw Notes]' in content

def test_cross_references(processor, setup_files):
    """Test cross-references between files."""
    input_dir, output_dir = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_files = processor.process(input_files[0], output_dir)
    
    # Check navigation links
    for f in output_files:
        content = f.read_text()
        assert 'Navigation:' in content
        if f.name == 'summary.md':
            assert '[Raw Notes]' in content
            assert '[Attachments]' in content
        elif f.name == 'raw_notes.md':
            assert '[Summary]' in content
            assert '[Attachments]' in content
        elif f.name == 'attachments.md':
            assert '[Summary]' in content
            assert '[Raw Notes]' in content

def test_long_path_handling(processor, tmp_path):
    """Test handling of file paths that are too long."""
    # Create a very long path
    long_path = "a" * 255 + ".md"  # Max filename length on most filesystems
    output_files = {
        'summary': tmp_path / long_path,
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    content = "# Test Document\nSome content"
    
    with pytest.raises(ProcessingError, match="File name too long"):
        processor.process(content, output_files)

def test_file_path_validation(processor, tmp_path):
    """Test file path validation including long paths and special characters."""
    # Test with long filename
    long_path = "a" * 255 + ".md"  # Max filename length on most filesystems
    output_files = {
        'summary': tmp_path / long_path,
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    content = "# Test Document\nSome content"
    
    with pytest.raises(ProcessingError, match="File name too long"):
        processor.process(content, output_files)
    
    # Test with spaces in path
    spaced_path = tmp_path / "test file.md"
    output_files = {
        'summary': spaced_path,
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should handle spaces correctly
    processor.process(content, output_files)
    assert output_files['summary'].exists()
    assert " " in str(output_files['summary'])

def test_concurrent_processing(tmp_path, processor_config, nova_config):
    """Test concurrent processing of multiple files."""
    num_files = 4
    contents = []
    output_files_list = []

    # Create test data
    for i in range(num_files):
        content_parts = []
        for j in range(100):  # 100 sections per file
            content_parts.extend([
                f"# Section {j}",
                "Content " * 10,
                f"--==ATTACHMENT_BLOCK: file{j}.txt==--",
                "Attachment " * 10,
                "--==ATTACHMENT_BLOCK_END==--"
            ])
        contents.append("\n\n".join(content_parts))

        output_files_list.append({
            'summary': tmp_path / f'summary_{i}.md',
            'raw_notes': tmp_path / f'raw_notes_{i}.md',
            'attachments': tmp_path / f'attachments_{i}.md'
        })

    # Process files concurrently
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(num_files):
            processor = ThreeFileSplitProcessor(processor_config, nova_config)
            futures.append(executor.submit(processor.process, contents[i], output_files_list[i]))
