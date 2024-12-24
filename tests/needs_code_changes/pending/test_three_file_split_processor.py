"""Tests for the ThreeFileSplitProcessor class."""

import pytest
import time
import concurrent.futures
from pathlib import Path
from nova.core.paths import PathsConfig
from nova.core.models import LoggingConfig
from nova.core.config import (
    NovaConfig, ProcessorConfig, ThreeFileSplitConfig,
    MarkdownConfig, EmbedConfig, ImageConfig, OfficeConfig,
    CacheConfig, OpenAIConfig, RetryConfig
)
from nova.core.errors import ProcessingError
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

@pytest.fixture
def nova_config(tmp_path):
    """Create a test NovaConfig instance."""
    paths_config = PathsConfig(
        base_dir=str(tmp_path),
        input_dir=str(tmp_path / 'input'),
        output_dir=str(tmp_path / 'output'),
        processing_dir=str(tmp_path / 'processing'),
        temp_dir=str(tmp_path / 'temp'),
        state_dir=str(tmp_path / 'state'),
        phase_dirs={
            'markdown_parse': str(tmp_path / 'phase' / 'markdown_parse'),
            'markdown_consolidate': str(tmp_path / 'phase' / 'markdown_consolidate'),
            'markdown_aggregate': str(tmp_path / 'phase' / 'markdown_aggregate'),
            'markdown_split': str(tmp_path / 'phase' / 'markdown_split')
        },
        image_dirs={
            'original': str(tmp_path / 'images' / 'original'),
            'processed': str(tmp_path / 'images' / 'processed'),
            'metadata': str(tmp_path / 'images' / 'metadata'),
            'cache': str(tmp_path / 'images' / 'cache')
        },
        office_dirs={
            'assets': str(tmp_path / 'office' / 'assets'),
            'temp': str(tmp_path / 'office' / 'temp')
        }
    )
    return NovaConfig(paths=paths_config)

@pytest.fixture
def processor_config():
    """Create a test ProcessorConfig instance."""
    return ThreeFileSplitConfig(
        enabled=True,
        name="three_file_split",
        processor="ThreeFileSplitProcessor",
        output_dir="output",
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
                        },
                        'content_preservation': {
                            'validate_input_size': True,
                            'validate_output_size': True,
                            'track_content_markers': True,
                            'verify_section_integrity': True
                        },
                        'cross_linking': True,
                        'preserve_headers': True
                    }
                }
            }
        }
    )

@pytest.fixture
def processor(nova_config, processor_config):
    """Create a test ThreeFileSplitProcessor instance."""
    # Create required directories
    for dir_path in [
        nova_config.paths.base_dir,
        nova_config.paths.input_dir,
        nova_config.paths.output_dir,
        nova_config.paths.processing_dir,
        nova_config.paths.temp_dir,
        nova_config.paths.state_dir,
        *nova_config.paths.phase_dirs.values(),
        *nova_config.paths.image_dirs.values(),
        *nova_config.paths.office_dirs.values()
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # Create state file
    state_file = Path(nova_config.paths.state_dir) / '.state'
    state_file.write_text('{}')

    return ThreeFileSplitProcessor(processor_config, nova_config)

@pytest.fixture
def setup_files(tmp_path):
    """Set up test files and directories."""
    input_dir = tmp_path / 'input'
    output_dir = tmp_path / 'output'
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create test input file
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--
# Test Document
This is a summary section.
[Link to attachment](test.txt)

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.
[another attachment](data.csv)

--==ATTACHMENTS==--
--==ATTACHMENT_BLOCK: test.txt==--
This is a test file content
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: data.csv==--
col1,col2
1,2
3,4
--==ATTACHMENT_BLOCK_END==--
""")

    return input_dir, output_dir

@pytest.fixture
def output_files(tmp_path):
    """Create output file paths."""
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'summary': output_dir / 'summary.md',
        'raw_notes': output_dir / 'raw_notes.md',
        'attachments': output_dir / 'attachments.md'
    }

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

def test_process_files(processor, setup_files, output_files):
    """Test processing input files."""
    input_dir, _ = setup_files
    input_files = list(input_dir.glob('*.md'))

    # Process files
    output_paths = processor.process(input_files[0], output_files)
    assert len(output_paths) == 3

    # Check output files exist
    for path in output_paths:
        assert path.exists()
        assert len(path.read_text()) > 0

def test_empty_input(processor, output_files):
    """Test processing with no input files."""
    with pytest.raises(ProcessingError, match="No input files provided"):
        processor.process(None, output_files)

def test_missing_sections(processor, setup_files, output_files):
    """Test processing file with missing sections."""
    input_dir, _ = setup_files

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
    output_paths = processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Check content
    assert "# Test Document" in output_files['summary'].read_text()
    assert "## Raw Notes" in output_files['raw_notes'].read_text()
    assert output_files['attachments'].read_text().strip() == ""

def test_invalid_markers(processor, setup_files, output_files):
    """Test processing file with invalid markers."""
    input_dir, _ = setup_files

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
        processor.process(test_file, output_files)

def test_empty_sections(processor, setup_files, output_files):
    """Test handling of empty content sections."""
    input_dir, _ = setup_files

    # Create test file with empty sections
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--

--==RAW_NOTES==--

--==ATTACHMENTS==--
""")

    with pytest.raises(ProcessingError, match="No content found in any section"):
        processor.process(test_file, output_files)

def test_basic_split(processor, setup_files, output_files):
    """Test basic split functionality."""
    input_dir, _ = setup_files

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
    output_paths = processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Check content
    assert "# Test Document" in output_files['summary'].read_text()
    assert "## Raw Notes" in output_files['raw_notes'].read_text()
    assert "No attachments" in output_files['attachments'].read_text()

def test_summary_content(processor, setup_files, output_files):
    """Test summary file content."""
    input_dir, _ = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_paths = processor.process(input_files[0], output_files)

    # Check summary content
    summary_content = output_files['summary'].read_text()
    assert "# Test Document" in summary_content
    assert "This is a summary section" in summary_content

def test_raw_notes_content(processor, setup_files, output_files):
    """Test raw notes file content."""
    input_dir, _ = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_paths = processor.process(input_files[0], output_files)

    # Check raw notes content
    raw_notes_content = output_files['raw_notes'].read_text()
    assert "## Raw Notes" in raw_notes_content
    assert "These are some raw notes" in raw_notes_content

def test_attachments_content(processor, setup_files, output_files):
    """Test attachments file content."""
    input_dir, _ = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_paths = processor.process(input_files[0], output_files)

    # Check attachments content
    attachments_content = output_files['attachments'].read_text()
    assert "--==ATTACHMENT_BLOCK: test.txt==--" in attachments_content
    assert "--==ATTACHMENT_BLOCK: data.csv==--" in attachments_content

def test_cross_references(processor, setup_files, output_files):
    """Test cross-references between files."""
    input_dir, _ = setup_files
    input_files = list(input_dir.glob('*.md'))
    output_paths = processor.process(input_files[0], output_files)

    # Check cross-references
    summary_content = output_files['summary'].read_text()
    raw_notes_content = output_files['raw_notes'].read_text()
    attachments_content = output_files['attachments'].read_text()

    assert "[Link to attachment](test.txt)" in summary_content
    assert "[another attachment](data.csv)" in raw_notes_content
    assert "This is a test file content" in attachments_content

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
