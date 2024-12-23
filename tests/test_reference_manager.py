"""Tests for the ReferenceManager class."""

import pytest
from nova.core.config import ProcessorConfig
from nova.processors.components.reference_manager import ReferenceManager

@pytest.fixture
def reference_manager():
    """Create a ReferenceManager instance for testing."""
    nova_config = ProcessorConfig(options={
        'input_dir': '/test/input',
        'output_dir': '/test/output'
    })
    return ReferenceManager(nova_config)

def test_generate_anchor_id(reference_manager):
    """Test generating anchor IDs."""
    # Test with filename only
    anchor1 = reference_manager.generate_anchor_id("test1.txt")
    assert len(anchor1) == 8
    assert anchor1.isalnum()

    # Test with filename and content
    anchor2 = reference_manager.generate_anchor_id("test2.txt", "content")
    assert len(anchor2) == 8
    assert anchor2.isalnum()

    # Test same input generates same ID
    anchor3 = reference_manager.generate_anchor_id("test1.txt")
    assert anchor3 == anchor1

    # Test different content generates different ID
    anchor4 = reference_manager.generate_anchor_id("test1.txt", "different")
    assert anchor4 != anchor1

def test_add_reference(reference_manager):
    """Test adding references between files."""
    reference_manager.add_reference("source.md", "target.md")
    
    # Check forward reference
    refs = reference_manager.get_references("source.md")
    assert "target.md" in refs
    
    # Check reverse reference
    back_refs = reference_manager.get_reverse_references("target.md")
    assert "source.md" in back_refs

def test_update_references(reference_manager):
    """Test updating references in content."""
    # Generate anchor ID
    filename = "test.txt"
    anchor_id = reference_manager.generate_anchor_id(filename)
    
    # Test content with attachment block
    content = f"Some content\n--==ATTACHMENT_BLOCK: {filename}==--\nMore content"
    updated = reference_manager.update_references(content, "source.md")
    
    # Check reference was updated
    assert f"[{filename}](attachments.md#{anchor_id})" in updated
    assert "--==ATTACHMENT_BLOCK:" not in updated

def test_add_navigation_links(reference_manager):
    """Test adding navigation links."""
    # Set up references
    source = "source.md"
    target1 = "target1.txt"
    target2 = "target2.txt"
    
    reference_manager.generate_anchor_id(target1)
    reference_manager.generate_anchor_id(target2)
    reference_manager.add_reference(source, target1)
    reference_manager.add_reference(source, target2)
    
    # Test adding navigation
    content = "Some content"
    updated = reference_manager.add_navigation_links(content, source)
    
    # Check navigation section was added
    assert "## Referenced Files" in updated
    assert f"[{target1}]" in updated
    assert f"[{target2}]" in updated

def test_validate_references(reference_manager):
    """Test reference validation."""
    # Generate anchor IDs first
    reference_manager.generate_anchor_id("a.md")
    reference_manager.generate_anchor_id("b.md")
    reference_manager.generate_anchor_id("c.md")

    # Set up circular reference
    reference_manager.add_reference("a.md", "b.md")
    reference_manager.add_reference("b.md", "c.md")
    reference_manager.add_reference("c.md", "a.md")

    # Test validation
    errors = reference_manager.validate_references()

    # Check errors were found
    assert len(errors) > 0
    assert "Circular reference detected" in errors[0]
    assert "a.md -> b.md -> c.md -> a.md" in errors[0]

def test_get_anchor_id(reference_manager):
    """Test retrieving anchor IDs."""
    filename = "test.txt"
    
    # Test missing anchor ID
    assert reference_manager.get_anchor_id(filename) is None
    
    # Test existing anchor ID
    anchor_id = reference_manager.generate_anchor_id(filename)
    assert reference_manager.get_anchor_id(filename) == anchor_id

def test_get_references(reference_manager):
    """Test retrieving references."""
    source = "source.md"
    target = "target.md"
    
    # Test no references
    assert len(reference_manager.get_references(source)) == 0
    
    # Test with reference
    reference_manager.add_reference(source, target)
    refs = reference_manager.get_references(source)
    assert len(refs) == 1
    assert target in refs

def test_get_reverse_references(reference_manager):
    """Test retrieving reverse references."""
    source = "source.md"
    target = "target.md"
    
    # Test no reverse references
    assert len(reference_manager.get_reverse_references(target)) == 0
    
    # Test with reverse reference
    reference_manager.add_reference(source, target)
    back_refs = reference_manager.get_reverse_references(target)
    assert len(back_refs) == 1
    assert source in back_refs