# Nova Document Processing Pipeline

A Python-based document processing pipeline for transforming various document formats into structured markdown with metadata.

## Overview

Nova processes documents through multiple phases:
1. Parse - Convert documents to markdown format
2. Disassemble - Split content into summary and notes
3. Split - Organize content into structured sections
4. Finalize - Generate final output with metadata

## Installation

```bash
# Install with pip
pip install -r requirements.txt

# Or with poetry
poetry install
```

## Usage

```python
from nova import Pipeline

pipeline = Pipeline()
pipeline.process("path/to/document")
```

## Configuration

### Logging

Nova uses environment variables for logging configuration:

```bash
# Set logging level (ERROR, WARNING, INFO, DEBUG)
export NOVA_LOG_LEVEL=DEBUG

# Run the pipeline with debug logging
./run_nova.sh
```

The logging level controls what information is displayed in the console:
- ERROR: Only show errors
- WARNING: Show warnings and errors
- INFO: Show informational messages, warnings, and errors
- DEBUG: Show all debug information, informational messages, warnings, and errors

## Development

### Prerequisites

- Python 3.8+
- Poetry (recommended) or pip
- pytest for testing

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/nova.git
cd nova

# Install dependencies with poetry
poetry install

# Or with pip
pip install -r requirements.txt
```

## Testing

The test suite uses pytest and includes unit tests, integration tests, and fixtures for testing various components of the pipeline.

### Running Tests

```bash
# Run all tests (without OpenAI API calls)
pytest

# Run specific test file
pytest tests/unit/test_handlers.py

# Run tests with coverage report
pytest --cov=nova tests/
```

### OpenAI API Testing

By default, all tests use mock responses for OpenAI API calls. To run tests with actual API calls:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Run tests with actual API calls
pytest --openai-api

# Run specific tests with API calls
pytest --openai-api tests/unit/test_handlers.py
```

### Test Structure

```
tests/
├── integration/
│   └── test_nova_pipeline.py    # End-to-end pipeline tests
└── unit/
    ├── test_core.py            # Core functionality tests
    ├── test_handlers.py        # Document handler tests
    ├── test_phase_parse.py     # Parse phase tests
    ├── test_phase_disassemble.py  # Disassembly phase tests
    ├── test_phase_split.py     # Split phase tests
    ├── test_phase_finalize.py  # Finalize phase tests
    ├── test_config_manager.py  # Configuration tests
    └── test_utils_path.py      # Path utility tests
```

### Test Resources

Test resources are included in the `tests/resources/` directory:
- `markdown/` - Sample markdown files
- `documents/` - Test PDF files
- `images/` - Test image files

### Testing Guidelines

1. **Mock by Default**: Tests use mock responses for external services by default
2. **API Testing**: Use `--openai-api` flag to test with actual API calls
3. **Test Resources**: Use provided test files in `tests/resources/`
4. **Async Testing**: Use pytest-asyncio for async function testing
5. **State Management**: Use provided fixtures for test state management

### Coverage Goals

- Minimum coverage target: 80%
- Focus on critical paths and error cases
- Include both success and failure scenarios

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (`pytest`)
5. Submit a pull request

## License



