# Nova

Nova is a document processing pipeline that extracts information from various file types and generates structured output.

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

## Usage

Run Nova with:
```bash
poetry run python -m nova.cli --config config/nova.yaml
```

Clean up processing artifacts with:
```bash
poetry run python -m nova.cleanup -a
```

## Testing

Nova uses pytest for testing. The test suite includes unit tests, integration tests, and API tests.

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

#### Image Handler Tests

The ImageHandler tests use three different modes:

1. **Mock API Mode (Default)**
   - Uses a mock OpenAI client that returns predefined responses
   - Fast and reliable for development
   - No API costs or rate limits
   - Run with: `poetry run pytest tests/handlers/test_image_handler.py`

2. **Real API Mode**
   - Tests against the actual OpenAI API
   - Requires valid API key in configuration
   - Useful for verifying API integration
   - Run with: `poetry run pytest tests/handlers/test_image_handler.py --openai-api`

3. **No API Mode**
   - Tests behavior when API is not configured
   - Verifies graceful fallback behavior
   - Run with any test command

### Writing Tests

Example test case with mocked API:
```python
@pytest.mark.handlers
def test_image_handler_mock_api(nova_config, test_image, mock_openai_client):
    handler = ImageHandler(nova_config)
    handler.vision_client = mock_openai_client
    metadata = handler.process_file(test_image)
    assert metadata.description == "This is a test image showing a simple geometric pattern."
```

Example test case with real API:
```python
@pytest.mark.handlers
@pytest.mark.openai_api
def test_image_handler_real_api(nova_config, test_image):
    handler = ImageHandler(nova_config)
    metadata = handler.process_file(test_image)
    assert len(metadata.description) > 0
```



