"""Tests for markdown consolidation processor."""

import os
from pathlib import Path
import pytest
import tempfile
import shutil

from nova.processors.markdown_consolidate import MarkdownConsolidateProcessor
from nova.core.config import ProcessorConfig, NovaConfig, PathsConfig
from nova.core.paths import NovaPaths
from nova.core.errors import ProcessingError

@pytest.fixture
def test_paths():
    """Create test paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        processing_dir = tmp_path / '_NovaProcessing'
        
        nova_paths = NovaPaths(
            base_dir=tmp_path,
            input_dir=tmp_path / '_NovaInput',
            output_dir=tmp_path / '_NovaOutput',
            processing_dir=processing_dir,
            temp_dir=processing_dir / 'temp',
            state_dir=processing_dir / '.state',
            phase_dirs={
                'markdown_parse': processing_dir / 'phases/markdown_parse',
                'markdown_consolidate': processing_dir / 'phases/markdown_consolidate'
            },
            image_dirs={
                'original': processing_dir / 'images/original',
                'processed': processing_dir / 'images/processed',
                'metadata': processing_dir / 'images/metadata',
                'cache': processing_dir / 'images/cache'
            },
            office_dirs={
                'assets': processing_dir / 'office/assets',
                'temp': processing_dir / 'office/temp'
            }
        )
        
        paths_config = PathsConfig(
            base_dir=nova_paths.base_dir,
            input_dir=nova_paths.input_dir,
            output_dir=nova_paths.output_dir,
            processing_dir=nova_paths.processing_dir,
            temp_dir=nova_paths.temp_dir,
            state_dir=nova_paths.state_dir,
            phase_dirs=nova_paths.phase_dirs,
            image_dirs=nova_paths.image_dirs,
            office_dirs=nova_paths.office_dirs
        )
        
        # Create required directories
        for dir_path in [paths_config.input_dir, paths_config.output_dir, paths_config.processing_dir, 
                        paths_config.temp_dir, paths_config.state_dir] + list(paths_config.phase_dirs.values()) + \
                       list(paths_config.image_dirs.values()) + list(paths_config.office_dirs.values()):
            dir_path.mkdir(parents=True, exist_ok=True)
            
        yield paths_config

@pytest.fixture
def processor(test_paths):
    """Create a markdown consolidate processor instance."""
    processor_config = ProcessorConfig(
        name="markdown_consolidate",
        output_dir=test_paths.phase_dirs['markdown_consolidate'],
        processor="MarkdownConsolidateProcessor"
    )
    nova_config = NovaConfig(paths=test_paths)
    return MarkdownConsolidateProcessor(processor_config, nova_config)

@pytest.fixture
def test_files(test_paths):
    """Create temporary test files and directories."""
    # Create main markdown file
    main_md = test_paths.input_dir / "test.md"
    main_md.write_text("# Main Document\n\nThis is the main content.")
    
    # Create attachments directory
    attachments_dir = test_paths.input_dir / "test"
    attachments_dir.mkdir()
    
    # Create attachment files
    attachment1 = attachments_dir / "attachment1.md"
    attachment1.write_text("## Attachment 1\n\nThis is attachment 1 content.")
    
    attachment2 = attachments_dir / "subdir" / "attachment2.md"
    attachment2.parent.mkdir(parents=True)
    attachment2.write_text("## Attachment 2\n\nThis is attachment 2 content.")
    
    yield {
        'main_md': main_md,
        'attachments_dir': attachments_dir,
        'output_dir': test_paths.output_dir
    }

def test_find_attachments_dir(processor, test_files):
    """Test finding attachments directory."""
    attachments_dir = processor._find_attachments_dir(test_files['main_md'])
    assert attachments_dir == test_files['attachments_dir']
    
def test_merge_attachments(processor, test_files):
    """Test merging attachments into main content."""
    content = "# Original Content"
    merged = processor._merge_attachments(content, test_files['attachments_dir'])
    
    assert "[Begin Attachment: attachment1.md]" in merged
    assert "This is attachment 1 content" in merged
    assert "[End Attachment: attachment1.md]" in merged
    
    assert "[Begin Attachment: subdir/attachment2.md]" in merged
    assert "This is attachment 2 content" in merged
    assert "[End Attachment: subdir/attachment2.md]" in merged
    
def test_process_with_attachments(processor, test_files):
    """Test processing a markdown file with attachments."""
    output_path = test_files['output_dir'] / "test.md"
    result = processor.process(test_files['main_md'], output_path)
    
    assert result == output_path
    assert output_path.exists()
    
    content = output_path.read_text()
    assert "# Main Document" in content
    assert "This is the main content" in content
    assert "[Begin Attachment: attachment1.md]" in content
    assert "This is attachment 1 content" in content
    assert "[Begin Attachment: subdir/attachment2.md]" in content
    assert "This is attachment 2 content" in content
    
def test_process_without_attachments(processor, test_files):
    """Test processing a markdown file without attachments."""
    # Create a markdown file without attachments
    no_attachments_md = test_files['main_md'].parent / "no_attachments.md"
    no_attachments_md.write_text("# No Attachments\n\nThis file has no attachments.")
    
    output_path = test_files['output_dir'] / "no_attachments.md"
    result = processor.process(no_attachments_md, output_path)
    
    assert result == output_path
    assert output_path.exists()
    
    content = output_path.read_text()
    assert "# No Attachments" in content
    assert "This file has no attachments" in content
    assert "[Begin Attachment:" not in content
    
def test_process_error_handling(processor):
    """Test error handling during processing."""
    with pytest.raises(ProcessingError):
        processor.process(
            Path("nonexistent.md"),
            Path("output.md")
        )