"""Test utilities for Nova."""
from pathlib import Path

def create_test_files(directory: Path) -> None:
    """Create test files for pipeline testing.
    
    Args:
        directory: Directory to create test files in.
    """
    # Create directory structure
    directory.mkdir(parents=True, exist_ok=True)
    
    # Create markdown file
    md_file = directory / "test.md"
    md_file.write_text("""# Test Document
    
This is a test markdown document.

## Features
- Basic formatting
- Lists
- Headers

## Code
```python
def test():
    print("Hello, world!")
```
""")
    
    # Create text file
    txt_file = directory / "test.txt"
    txt_file.write_text("This is a test text file.\nIt has multiple lines.\nEach line tests text handling.")
    
    # Create PDF file
    pdf_file = directory / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%Test PDF content")  # Minimal PDF content
    
    # Create image file
    jpg_file = directory / "test.jpg"
    jpg_file.write_bytes(b"Test JPEG content")  # Minimal JPEG content 