"""Unit tests for the ReferenceManager class."""

import pytest
from pathlib import Path
from nova.core.reference_manager import ReferenceManager, Reference

@pytest.fixture
def ref_manager():
    """Create a reference manager instance."""
    return ReferenceManager()

@pytest.fixture
def test_content():
    """Create test content with references."""
    return """# Test Document

Here's a reference to [ATTACH:PDF:document] and an image ![ATTACH:IMAGE:diagram].

See also [NOTE:meeting-notes] for more details.

Another reference to [ATTACH:DOC:report] here.
"""

def test_extract_references(ref_manager, test_content, tmp_path):
    """Test reference extraction from content."""
    source_file = tmp_path / "test.md"
    
    # Extract references
    references = ref_manager.extract_references(test_content, source_file)
    
    # Verify correct number of references found
    assert len(references) == 4
    
    # Verify reference types
    ref_types = [ref.ref_type for ref in references]
    assert ref_types.count('ATTACH') == 3
    assert ref_types.count('NOTE') == 1
    
    # Verify specific references
    ref_ids = [ref.ref_id for ref in references]
    assert 'document' in ref_ids
    assert 'diagram' in ref_ids
    assert 'meeting-notes' in ref_ids
    assert 'report' in ref_ids
    
    # Verify context is captured
    for ref in references:
        assert ref.context is not None
        assert len(ref.context.split('\n')) <= 7  # Max 7 lines of context
        
def test_validate_references(ref_manager, tmp_path):
    """Test reference validation."""
    # Create test files
    source_file = tmp_path / "test.md"
    attachment = tmp_path / "document.pdf"
    note_file = tmp_path / "Raw Notes.md"
    
    # Create valid attachment
    attachment.touch()
    
    # Create note file with valid section
    note_file.write_text("## [NOTE:meeting-notes]\nNote content")
    
    # Create test content
    content = """# Test Document
    
    Valid attachment: [ATTACH:PDF:document]
    Invalid attachment: [ATTACH:PDF:missing]
    Valid note: [NOTE:meeting-notes]
    Invalid note: [NOTE:missing-note]
    """
    
    # Extract references
    references = ref_manager.extract_references(content, source_file)
    
    # Set target files
    for ref in references:
        if ref.ref_id == 'document':
            ref.target_file = attachment
        elif ref.ref_id == 'meeting-notes':
            ref.target_file = note_file
        elif ref.ref_id == 'missing':
            ref.target_file = tmp_path / "missing.pdf"
        elif ref.ref_id == 'missing-note':
            ref.target_file = note_file
    
    # Validate references
    errors = ref_manager.validate_references(tmp_path)
    
    # Verify errors
    assert len(errors) == 2
    assert any('missing.pdf' in error for error in errors)
    assert any('missing-note' in error for error in errors)
    
    # Verify invalid references list
    invalid_refs = ref_manager.get_invalid_references()
    assert len(invalid_refs) == 2
    invalid_ids = [ref.ref_id for ref in invalid_refs]
    assert 'missing' in invalid_ids
    assert 'missing-note' in invalid_ids
    
def test_update_references(ref_manager, tmp_path):
    """Test reference updating when files move."""
    # Create test files
    old_path = tmp_path / "old.md"
    new_path = tmp_path / "new.md"
    source_file = tmp_path / "test.md"
    
    # Create test content
    content = "Reference to [ATTACH:PDF:document]"
    
    # Extract reference
    references = ref_manager.extract_references(content, source_file)
    assert len(references) == 1
    
    # Set target file
    references[0].target_file = old_path
    
    # Update reference
    ref_manager.update_references(old_path, new_path)
    
    # Verify reference was updated
    updated_refs = ref_manager.get_file_references(source_file)
    assert len(updated_refs) == 1
    assert updated_refs[0].target_file == new_path
    
def test_cleanup_references(ref_manager, tmp_path):
    """Test reference cleanup."""
    source_file = tmp_path / "test.md"
    
    # Create test content with invalid references
    content = """# Test
    
    [ATTACH:PDF:missing1]
    [ATTACH:PDF:missing2]
    [NOTE:missing-note]
    """
    
    # Extract references
    references = ref_manager.extract_references(content, source_file)
    assert len(references) == 3
    
    # Mark all as invalid
    for ref in references:
        ref.target_file = tmp_path / "missing.pdf"
        ref.is_valid = False
        ref_manager.invalid_references.append(ref)
    
    # Cleanup references
    ref_manager.cleanup_references()
    
    # Verify all references were removed
    assert len(ref_manager.references) == 0
    assert len(ref_manager.file_references) == 0
    assert len(ref_manager.invalid_references) == 0 