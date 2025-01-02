"""Unit tests for the MarkdownProcessor class."""

import pytest
from pathlib import Path
from nova.processor.markdown_processor import MarkdownProcessor

@pytest.fixture
def processor():
    """Create a markdown processor instance."""
    return MarkdownProcessor()

@pytest.fixture
def test_content():
    """Create test content with references."""
    return """# Test Document

Here's a reference to [ATTACH:PDF:document] and an image ![ATTACH:IMAGE:diagram].

See also [NOTE:meeting-notes] for more details.

Another reference to [ATTACH:DOC:report] here.

--==RAW NOTES==--
More content with [ATTACH:PDF:notes] reference.
"""

def test_extract_attachments(processor, test_content, tmp_path):
    """Test attachment extraction with ReferenceManager integration."""
    source_file = tmp_path / "test.md"
    
    # Create test files to make references valid
    (tmp_path / "document.pdf").touch()
    (tmp_path / "diagram.png").touch()
    (tmp_path / "report.doc").touch()
    (tmp_path / "notes.pdf").touch()
    
    # Extract attachments
    attachments = processor._extract_attachments(str(test_content), str(source_file))
    
    # Verify correct number of attachments found
    assert len(attachments) == 4  # document, diagram, report, notes
    
    # Verify attachment types
    types = [a['type'] for a in attachments]
    assert 'PDF' in types
    assert 'IMAGE' in types
    assert 'DOC' in types
    
    # Verify references are correctly formatted
    refs = [a['ref'] for a in attachments]
    assert '[ATTACH:PDF:document]' in refs
    assert '[ATTACH:IMAGE:diagram]' in refs
    assert '[ATTACH:DOC:report]' in refs
    assert '[ATTACH:PDF:notes]' in refs
    
    # Verify context is captured
    for attachment in attachments:
        assert attachment['context'] is not None
        assert len(attachment['context'].split('\n')) <= 7  # Max 7 lines
        
def test_build_attachments_markdown(processor, test_content, tmp_path):
    """Test building attachments markdown with ReferenceManager integration."""
    source_file = tmp_path / "test.md"
    
    # Create test files
    (tmp_path / "document.pdf").touch()
    (tmp_path / "diagram.png").touch()
    (tmp_path / "report.doc").touch()
    (tmp_path / "notes.pdf").touch()
    
    # Extract attachments
    attachments = processor._extract_attachments(str(test_content), str(source_file))
    
    # Build markdown
    markdown = processor._build_attachments_markdown(attachments)
    
    # Verify structure
    assert markdown.startswith("# Attachments")
    
    # Verify all references are included
    assert '[ATTACH:PDF:document]' in markdown
    assert '[ATTACH:IMAGE:diagram]' in markdown
    assert '[ATTACH:DOC:report]' in markdown
    assert '[ATTACH:PDF:notes]' in markdown
    
    # Verify sections are organized by type
    assert "### PDF Files" in markdown
    assert "### IMAGE Files" in markdown
    assert "### DOC Files" in markdown
    
    # Verify context is included
    assert "Context:" in markdown
    assert "> Here's a reference to" in markdown
    
def test_empty_attachments(processor):
    """Test handling of content with no attachments."""
    content = """# Test Document
    
    No attachments here.
    Just regular content.
    """
    
    # Extract attachments
    attachments = processor._extract_attachments(content, "test.md")
    assert len(attachments) == 0
    
    # Build markdown
    markdown = processor._build_attachments_markdown(attachments)
    assert markdown == "# Attachments\n\nNo attachments found."
    
def test_reference_context(processor, tmp_path):
    """Test context extraction for references."""
    content = """# Test Document
    
    First paragraph with no references.
    
    Second paragraph with [ATTACH:PDF:doc1] reference
    and some context around it.
    More context here.
    
    * List item 1
    * List item with [ATTACH:PDF:doc2] reference
    * List item 3
    
    Final paragraph.
    """
    
    source_file = tmp_path / "test.md"
    
    # Create test files
    (tmp_path / "doc1.pdf").touch()
    (tmp_path / "doc2.pdf").touch()
    
    attachments = processor._extract_attachments(str(content), str(source_file))
    
    # Verify doc1 context
    doc1 = next(a for a in attachments if a['ref'] == '[ATTACH:PDF:doc1]')
    assert "Second paragraph" in doc1['context']
    assert "context around it" in doc1['context']
    
    # Verify doc2 context (should include list items)
    doc2 = next(a for a in attachments if a['ref'] == '[ATTACH:PDF:doc2]')
    assert "List item 1" in doc2['context']
    assert "List item 3" in doc2['context']
    
def test_invalid_references(processor, tmp_path):
    """Test handling of invalid references."""
    content = """# Test Document
    
    Valid reference: [ATTACH:PDF:doc1]
    Invalid reference: [ATTACH:PDF:missing]
    """
    
    source_file = tmp_path / "test.md"
    
    # Create only one test file
    (tmp_path / "doc1.pdf").touch()
    
    attachments = processor._extract_attachments(str(content), str(source_file))
    
    # Verify both references are found
    assert len(attachments) == 2
    
    # Verify valid reference
    valid = next(a for a in attachments if a['id'] == 'doc1')
    assert valid['is_valid']
    assert valid['target_file'] is not None
    
    # Verify invalid reference
    invalid = next(a for a in attachments if a['id'] == 'missing')
    assert not invalid['is_valid']
    
    # Check markdown output includes invalid marker
    markdown = processor._build_attachments_markdown(attachments)
    assert '[ATTACH:PDF:missing] (INVALID)' in markdown
    
def test_reference_updates(processor, tmp_path):
    """Test updating references when files move."""
    content = """# Test Document
    Reference to [ATTACH:PDF:doc1]
    """
    
    source_file = tmp_path / "test.md"
    old_path = tmp_path / "old.pdf"
    new_path = tmp_path / "new.pdf"
    
    # Create and process initial file
    old_path.touch()
    attachments = processor._extract_attachments(str(content), str(source_file))
    
    # Verify initial state
    assert len(attachments) == 1
    assert attachments[0]['target_file'] == str(old_path)
    
    # Update reference
    processor.update_references(old_path, new_path)
    
    # Process content again
    new_path.touch()
    old_path.unlink()
    attachments = processor._extract_attachments(str(content), str(source_file))
    
    # Verify reference was updated
    assert len(attachments) == 1
    assert attachments[0]['target_file'] == str(new_path) 