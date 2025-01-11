# Nova Style Guide

## Code Formatting

### Black

We use Black for code formatting with a line length of 88 characters. Black is non-negotiable and maintains consistency across the codebase.

```bash
# Format a file
poetry run black src/nova/file.py

# Format the entire project
poetry run black .
```

### Import Ordering

Imports should be organized using `ruff` in the following order:

1. Standard library imports
2. Third-party imports
3. Local application imports

Example:
```python
import os
import time
from typing import Optional, List

import numpy as np
import faiss
from prometheus_client import Counter

from nova.types import Chunk
from nova.utils import setup_logging
```

## Code Style

### Type Hints

- All function arguments and return values must have type hints
- Use `Optional` for parameters that can be None
- Use `Any` sparingly and only when absolutely necessary

```python
def process_data(
    data: List[str],
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """Process data with optional threshold."""
```

### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def complex_function(
    param1: str,
    param2: Optional[int] = None
) -> bool:
    """Short description of function.

    Longer description if needed, explaining complex logic
    or important details.

    Args:
        param1: Description of param1
        param2: Description of param2, defaults to None

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this error is raised
    """
```

### Error Handling

1. Use specific exceptions:
```python
# Good
raise ValueError("Invalid dimension: must be positive")

# Bad
raise Exception("Something went wrong")
```

2. Always include error messages:
```python
try:
    process_data()
except ValueError as e:
    logger.error(f"Data processing failed: {e}")
    raise
```

### Logging

Use the standard logging module with appropriate levels:

```python
import logging

logger = logging.getLogger(__name__)

# Debug: Detailed information for debugging
logger.debug("Processing vector %d of %d", i, total)

# Info: Confirmation that things are working
logger.info("Successfully initialized vector store")

# Warning: Something unexpected, but not critical
logger.warning("GPU not available, falling back to CPU")

# Error: Something failed but application continues
logger.error("Failed to process document: %s", e)

# Critical: Application cannot continue
logger.critical("Database connection failed")
```

## Project Structure

### Module Organization

```
src/nova/
├── __init__.py
├── types.py           # Core data types
├── processing/        # Data processing modules
│   ├── __init__.py
│   ├── chunking.py
│   └── vector_store.py
├── monitoring/        # Monitoring and metrics
│   ├── __init__.py
│   ├── metrics.py
│   └── alerts.py
└── utils/            # Utility functions
    ├── __init__.py
    └── helpers.py
```

### File Naming

- Use lowercase with underscores
- Be descriptive but concise
- Include type in name if applicable (e.g., `user_types.py`)

## Testing

### Test Organization

```python
# test_module.py
class TestClassName:
    """Tests for ClassName."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = ClassName()

    def test_specific_function(self):
        """Test specific functionality."""
        result = self.instance.function()
        assert result == expected
```

### Test Naming

- Use descriptive names that explain the test
- Include the scenario and expected outcome
- Use consistent naming patterns

```python
def test_search_with_empty_index_returns_empty_list():
    ...

def test_add_vectors_with_invalid_dimension_raises_error():
    ...
```

## Performance

### Vector Operations

- Use numpy operations instead of loops
- Pre-allocate arrays when size is known
- Use appropriate data types (e.g., float32 for vectors)

```python
# Good
vectors = np.zeros((n_vectors, dim), dtype=np.float32)

# Bad
vectors = []
for _ in range(n_vectors):
    vectors.append(np.zeros(dim))
```

### Memory Management

- Clean up large objects when no longer needed
- Use context managers for resource management
- Monitor memory usage in long-running operations

```python
# Good
with tempfile.NamedTemporaryFile() as temp:
    process_large_file(temp.name)
# File is automatically cleaned up

# Bad
temp = create_temp_file()
process_large_file(temp)
# File might not be cleaned up
```

## Documentation

### Code Comments

- Use comments to explain why, not what
- Keep comments up to date with code changes
- Use TODO comments for future work

```python
# Good
# Skip cleanup if no vectors to avoid unnecessary index rebuild
if not vectors_to_remove:
    return

# Bad
# Remove vectors
remove_vectors()
```

### API Documentation

- Document all public APIs
- Include examples for complex functionality
- Keep documentation in sync with code

## Version Control

### Commit Messages

Follow conventional commits:
```
feat: add vector store GPU support
fix: correct dimension mismatch in search
docs: update installation instructions
test: add performance benchmarks
refactor: optimize cleanup process
```

### Branch Naming

Use descriptive branch names:
```
feature/gpu-support
bugfix/dimension-mismatch
docs/installation-guide
```

## Development Workflow

1. Install pre-commit hooks:
```bash
poetry run pre-commit install
```

2. Run tests before committing:
```bash
poetry run pytest
```

3. Check type hints:
```bash
poetry run mypy src/nova
```

4. Run linting:
```bash
poetry run ruff check .
```

5. Format code:
```bash
poetry run black .
``` 