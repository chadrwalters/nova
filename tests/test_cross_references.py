"""Cross-reference validation tests for the processing pipeline."""

import pytest
from pathlib import Path
from typing import Dict, Any

from nova.processors.three_file_split_processor import ThreeFileSplitProcessor
from nova.core.errors import ProcessingError

@pytest.fixture
def processor_config():
    """Create a processor config for testing."""
    return {
        'output_files': {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        },
        'section_markers': {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW NOTES==--',
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

@pytest.fixture
def nova_config(tmp_path):
    """Create a nova config for testing."""
    return {
        'paths': {
            'base_dir': str(tmp_path),
            'input_dir': str(tmp_path / 'input'),
            'output_dir': str(tmp_path / 'output'),
            'processing_dir': str(tmp_path / 'processing'),
            'temp_dir': str(tmp_path / 'temp'),
            'state_dir': str(tmp_path / 'state'),
            'phase_dirs': {
                'markdown_parse': str(tmp_path / 'phases/markdown_parse'),
                'markdown_consolidate': str(tmp_path / 'phases/markdown_consolidate'),
                'markdown_aggregate': str(tmp_path / 'phases/markdown_aggregate'),
                'markdown_split': str(tmp_path / 'phases/markdown_split')
            },
            'image_dirs': {
                'original': str(tmp_path / 'images/original'),
                'processed': str(tmp_path / 'images/processed'),
                'metadata': str(tmp_path / 'images/metadata'),
                'cache': str(tmp_path / 'images/cache')
            },
            'office_dirs': {
                'assets': str(tmp_path / 'office/assets'),
                'temp': str(tmp_path / 'office/temp')
            }
        }
    }

@pytest.fixture
def split_processor(processor_config, nova_config):
    """Create a split processor instance."""
    return ThreeFileSplitProcessor(processor_config, nova_config)

def test_basic_cross_references(split_processor, tmp_path):
    """Test basic cross-reference handling."""
    content = """
# Test Document

See [[Reference 1]] for details.

--==ATTACHMENT_BLOCK: test1.txt==--
This is Reference 1
--==ATTACHMENT_BLOCK_END==--

Also see [[Reference 2]].

--==ATTACHMENT_BLOCK: test2.txt==--
This is Reference 2
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    metrics = split_processor.process(content, output_files)
    
    # Check that references are preserved
    summary_content = output_files['summary'].read_text()
    attachments_content = output_files['attachments'].read_text()
    
    assert "[[Reference 1]]" in summary_content
    assert "[[Reference 2]]" in summary_content
    assert "This is Reference 1" in attachments_content
    assert "This is Reference 2" in attachments_content

def test_broken_cross_references(split_processor, tmp_path):
    """Test handling of broken cross-references."""
    content = """
# Test Document

See [[Missing Reference]] for details.

--==ATTACHMENT_BLOCK: test.txt==--
Some content
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should process but log warning
    with pytest.warns(UserWarning, match="Missing reference target"):
        split_processor.process(content, output_files)

def test_circular_references(split_processor, tmp_path):
    """Test handling of circular references."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK: test1.txt==--
See [[Reference 2]]
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test2.txt==--
See [[Reference 1]]
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should process but log warning
    with pytest.warns(UserWarning, match="Circular reference detected"):
        split_processor.process(content, output_files)

def test_duplicate_references(split_processor, tmp_path):
    """Test handling of duplicate references."""
    content = """
# Test Document

See [[Same Reference]] here.

--==ATTACHMENT_BLOCK: test1.txt==--
This is Same Reference
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test2.txt==--
This is also Same Reference
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Duplicate reference target"):
        split_processor.process(content, output_files)

def test_nested_references(split_processor, tmp_path):
    """Test handling of nested references."""
    content = """
# Test Document

See [[Outer Reference]].

--==ATTACHMENT_BLOCK: outer.txt==--
This references [[Inner Reference]]
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: inner.txt==--
Inner content
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    metrics = split_processor.process(content, output_files)
    
    # Check that nested references are preserved
    attachments_content = output_files['attachments'].read_text()
    assert "[[Inner Reference]]" in attachments_content
    assert "Inner content" in attachments_content

def test_reference_case_sensitivity(split_processor, tmp_path):
    """Test case sensitivity in references."""
    content = """
# Test Document

See [[Reference]] and [[REFERENCE]].

--==ATTACHMENT_BLOCK: test.txt==--
This is Reference
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should treat references as case-sensitive
    with pytest.warns(UserWarning, match="Missing reference target"):
        split_processor.process(content, output_files)

def test_reference_special_characters(split_processor, tmp_path):
    """Test references with special characters."""
    content = """
# Test Document

See [[Reference with spaces]] and [[Reference-with-dashes]].
Also [[Reference_with_underscores]] and [[Reference.with.dots]].

--==ATTACHMENT_BLOCK: test1.txt==--
Content with spaces
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test2.txt==--
Content with-dashes
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test3.txt==--
Content_with_underscores
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test4.txt==--
Content.with.dots
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    metrics = split_processor.process(content, output_files)
    
    # Check that special characters are handled
    summary_content = output_files['summary'].read_text()
    assert all(ref in summary_content for ref in [
        "[[Reference with spaces]]",
        "[[Reference-with-dashes]]",
        "[[Reference_with_underscores]]",
        "[[Reference.with.dots]]"
    ])

def test_reference_unicode(split_processor, tmp_path):
    """Test references with Unicode characters."""
    content = """
# Test Document

See [[引用]] and [[Référence]].

--==ATTACHMENT_BLOCK: test1.txt==--
Chinese content
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test2.txt==--
French content
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    metrics = split_processor.process(content, output_files)
    
    # Check that Unicode references are preserved
    summary_content = output_files['summary'].read_text()
    assert "[[引用]]" in summary_content
    assert "[[Référence]]" in summary_content

def test_reference_validation_chain(split_processor, tmp_path):
    """Test validation of reference chains."""
    content = """
# Test Document

See [[First]] which leads to [[Second]].

--==ATTACHMENT_BLOCK: first.txt==--
See [[Second]] for more details.
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: second.txt==--
See [[Third]] for final details.
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should warn about missing final reference
    with pytest.warns(UserWarning, match="Missing reference target: Third"):
        split_processor.process(content, output_files)

def test_reference_in_metadata(split_processor, tmp_path):
    """Test handling of references in metadata."""
    content = """
---
title: Test Document
related: [[Related Document]]
---

# Main Content

--==ATTACHMENT_BLOCK: test.txt==--
Some content
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should ignore references in metadata
    metrics = split_processor.process(content, output_files)
    
    summary_content = output_files['summary'].read_text()
    assert "[[Related Document]]" in summary_content  # Reference preserved but not processed

def test_reference_validation_summary(split_processor, tmp_path):
    """Test generation of reference validation summary."""
    content = """
# Test Document

See [[Valid Reference]] and [[Missing Reference]].

--==ATTACHMENT_BLOCK: test.txt==--
This is Valid Reference
Also see [[Another Missing]]
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Process with validation summary
    with pytest.warns(UserWarning) as warnings:
        metrics = split_processor.process(content, output_files)
    
    # Check validation messages
    warning_messages = [str(w.message) for w in warnings]
    assert any("Missing reference target: Missing Reference" in msg for msg in warning_messages)
    assert any("Missing reference target: Another Missing" in msg for msg in warning_messages)
    assert len([msg for msg in warning_messages if "Missing reference target" in msg]) == 2 