# Nova

Nova is a document processing pipeline that extracts information from various file types and generates structured output with comprehensive metadata validation.

## Installation

1. Clone the repository
2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up pre-commit hooks:
```bash
poetry add pre-commit --dev
pre-commit install
```

## Development Standards

Nova uses several tools to maintain code quality:

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (black profile)
- **flake8**: Code linting
- **mypy**: Static type checking
- **bandit**: Security checks
- **commitizen**: Commit message standardization

These are enforced via pre-commit hooks. The hooks will run automatically on commit.

## Features

### Document Processing
Nova processes documents through a series of well-defined phases, each responsible for a specific aspect of document transformation. For detailed information about the processing phases and their implementation, see [Phases Documentation](docs/phases.md).

Key features include:
- Multi-phase document processing
- Structured markdown output
- Metadata validation and tracking
- Embedded document support
- Cross-reference management

### Metadata System
- Comprehensive validation framework
- Type-specific validation rules
- Cross-phase version tracking
- Related metadata validation
- Reference integrity checks

### File Type Support
Nova provides comprehensive support for various file formats through specialized handlers. For detailed information about handler implementations and features, see [Handlers Documentation](docs/handlers.md).

Supported formats include:

- **Documents**: `.docx`, `.doc`, `.rtf`, `.odt`, `.pdf`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.heic`, `.webp`
- **Text**: `.txt`
- **Markdown**: `.md`, `.markdown`
- **Spreadsheets**: `.xlsx`, `.xls`, `.csv`
- **Web**: `.html`, `.htm`
- **Video**: `.mp4`, `.mov`, `.avi`, `.mkv`
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.ogg`
- **Archives**: `.zip`, `.tar`, `.gz`, `.7z`

## Usage

Run Nova with:
```bash
poetry run nova.context_processor.cli --config config/nova.yaml
```

Clean up processing artifacts with:
```bash
poetry run nova.context_processor.cleanup -a
```

## Testing

Nova uses pytest for testing. The test suite includes:
- Unit tests for components
- Integration tests for workflows
- Validation tests for metadata
- Handler-specific tests
- API integration tests

### Running Tests

Run all tests (excluding API tests):
```bash
poetry run pytest
```

Run tests with OpenAI API access:
```bash
poetry run pytest --openai-api
```

### Testing Strategy

#### Handler Tests

The handlers can be tested in different modes:

1. **Mock Mode (Default)**
   - Uses mock clients/APIs
   - Fast and reliable
   - No external dependencies
   - Run with: `poetry run pytest tests/handlers/`

2. **Integration Mode**
   - Tests against real APIs/services
   - Requires configuration
   - Validates real-world behavior
   - Run with: `poetry run pytest tests/handlers/ --integration`

3. **Validation Mode**
   - Tests metadata validation
   - Verifies error handling
   - Checks data integrity
   - Run with: `poetry run pytest tests/validation/`

### Writing Tests

Example test case with metadata validation:
```python
def test_metadata_validation(validator):
    metadata = DocumentMetadata(
        file_path="test.docx",
        page_count=10,
        word_count=1000
    )
    errors = validator.validate_schema(metadata)
    assert not errors  # Validates successfully
```

For more details, see the [Architecture Documentation](docs/architecture.md).



