# Nova

Nova is a document processing pipeline that extracts information from various file types and generates structured output.

## Installation

1. Clone the repository
2. Install dependencies using Poetry:
```bash
poetry install
```

## Usage

Run Nova with:
```bash
./run_nova.sh
```

Clean up processing artifacts with:
```bash
./cleanup.sh -a
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



