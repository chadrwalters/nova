import threading
from typing import Optional
from contextlib import contextmanager

# Initialize thread-local storage
_local = threading.local()

@contextmanager
def document_context():
    """Context manager for document processing state."""
    # Initialize thread-local storage
    if not hasattr(_local, 'current_frontmatter'):
        _local.current_frontmatter = {}
        
    try:
        yield _local
    finally:
        # Clean up
        _local.current_frontmatter = {}

def get_current_frontmatter() -> dict:
    """Get current document's frontmatter."""
    if not hasattr(_local, 'current_frontmatter'):
        _local.current_frontmatter = {}
    return _local.current_frontmatter

def set_current_frontmatter(frontmatter: dict) -> None:
    """Set current document's frontmatter."""
    _local.current_frontmatter = frontmatter 