"""Test cross-reference functionality."""

import pytest
from nova.core.config import PathsConfig, NovaConfig
from nova.processors.components.cross_references import CrossReferenceManager

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
def cross_reference_manager(nova_config):
    """Create a test CrossReferenceManager instance."""
    return CrossReferenceManager(nova_config)

def test_basic_cross_references(cross_reference_manager, tmp_path):
    """Test basic cross-reference functionality."""
    # Create test files
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"
    file1.write_text("# Test File 1\nSee [Test File 2](file2.md)")
    file2.write_text("# Test File 2\nSee [Test File 1](file1.md)")

    # Add references
    cross_reference_manager.add_reference(str(file1), str(file2), "Test File 2")
    cross_reference_manager.add_reference(str(file2), str(file1), "Test File 1")

    # Verify references
    refs = cross_reference_manager.get_references(str(file1))
    assert len(refs) == 1
    assert refs[0].target == str(file2)
    assert refs[0].text == "Test File 2"

def test_broken_cross_references(cross_reference_manager, tmp_path):
    """Test handling of broken cross-references."""
    file1 = tmp_path / "file1.md"
    file1.write_text("# Test File 1\nSee [Missing File](missing.md)")

    # Add broken reference
    cross_reference_manager.add_reference(str(file1), str(tmp_path / "missing.md"), "Missing File")

    # Verify validation catches broken reference
    errors = cross_reference_manager.validate_references()
    assert len(errors) == 1
    assert "missing.md" in errors[0]

def test_circular_references(cross_reference_manager, tmp_path):
    """Test detection of circular references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"
    file3 = tmp_path / "file3.md"

    # Create circular reference chain
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2")
    cross_reference_manager.add_reference(str(file2), str(file3), "File 3")
    cross_reference_manager.add_reference(str(file3), str(file1), "File 1")

    # Verify circular reference detection
    errors = cross_reference_manager.validate_references()
    assert len(errors) == 1
    assert "circular reference" in errors[0].lower()

def test_duplicate_references(cross_reference_manager, tmp_path):
    """Test handling of duplicate references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"

    # Add duplicate references
    cross_reference_manager.add_reference(str(file1), str(file2), "Test File 2")
    cross_reference_manager.add_reference(str(file1), str(file2), "Test File 2")

    # Verify only one reference is stored
    refs = cross_reference_manager.get_references(str(file1))
    assert len(refs) == 1

def test_nested_references(cross_reference_manager, tmp_path):
    """Test handling of nested references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"
    file3 = tmp_path / "file3.md"

    # Create nested reference chain
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2")
    cross_reference_manager.add_reference(str(file2), str(file3), "File 3")

    # Verify nested references
    refs = cross_reference_manager.get_references(str(file1))
    nested_refs = cross_reference_manager.get_references(str(file2))
    assert len(refs) == 1
    assert len(nested_refs) == 1

def test_reference_case_sensitivity(cross_reference_manager, tmp_path):
    """Test case sensitivity in references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "FILE2.md"

    # Add references with different case
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2")
    cross_reference_manager.add_reference(str(file1), str(file2).lower(), "File 2")

    # Verify case-insensitive handling
    refs = cross_reference_manager.get_references(str(file1))
    assert len(refs) == 1

def test_reference_special_characters(cross_reference_manager, tmp_path):
    """Test handling of special characters in references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file-with-special-chars!@#$.md"

    # Add reference with special characters
    cross_reference_manager.add_reference(str(file1), str(file2), "Special File")

    # Verify reference handling
    refs = cross_reference_manager.get_references(str(file1))
    assert len(refs) == 1
    assert refs[0].target == str(file2)

def test_reference_unicode(cross_reference_manager, tmp_path):
    """Test handling of Unicode characters in references."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file-with-unicode-αβγ.md"

    # Add reference with Unicode characters
    cross_reference_manager.add_reference(str(file1), str(file2), "Unicode File")

    # Verify reference handling
    refs = cross_reference_manager.get_references(str(file1))
    assert len(refs) == 1
    assert refs[0].target == str(file2)

def test_reference_validation_chain(cross_reference_manager, tmp_path):
    """Test validation of reference chains."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"
    file3 = tmp_path / "file3.md"

    # Create reference chain
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2")
    cross_reference_manager.add_reference(str(file2), str(file3), "File 3")

    # Verify reference chain validation
    errors = cross_reference_manager.validate_references()
    assert len(errors) == 0

def test_reference_in_metadata(cross_reference_manager, tmp_path):
    """Test handling of references in metadata."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"

    # Add reference in metadata
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2", is_metadata=True)

    # Verify metadata reference handling
    refs = cross_reference_manager.get_references(str(file1), include_metadata=True)
    assert len(refs) == 1
    assert refs[0].is_metadata

def test_reference_validation_summary(cross_reference_manager, tmp_path):
    """Test generation of reference validation summary."""
    file1 = tmp_path / "file1.md"
    file2 = tmp_path / "file2.md"
    missing = tmp_path / "missing.md"

    # Add valid and invalid references
    cross_reference_manager.add_reference(str(file1), str(file2), "File 2")
    cross_reference_manager.add_reference(str(file1), str(missing), "Missing File")

    # Verify validation summary
    summary = cross_reference_manager.get_validation_summary()
    assert "total references" in summary.lower()
    assert "broken references" in summary.lower()
    assert "1 broken" in summary 