# Nova Document Processor

A modern, async document processing pipeline for converting markdown to PDF with embedded document support and advanced validation.

## Features

### Core Processing
- Async markdown processing pipeline
- Secure content validation and sanitization
- Frontmatter extraction and validation
- Special character handling
- Base64 content processing
- Structured error handling

### Document Support
- **Markdown Files**
  - UTF-8 encoding validation
  - Structure validation
  - Content safety checks
  - Frontmatter processing
  
- **Embedded Documents**
  - Word (.docx, .doc)
    - Full text extraction
    - Metadata preservation
    - Author and timestamp tracking
    
  - PDF (.pdf)
    - Text extraction
    - Metadata extraction
    - Reference validation
    
  - PowerPoint (.pptx, .ppt)
    - Slide content extraction
    - Notes processing
    - Metadata tracking

### Security Features
- Path traversal protection
- Content safety validation
- Secure file handling
- Permission validation
- Size limit enforcement

### Metadata Management
- Frontmatter validation
- Filename metadata extraction
- Document reference tracking
- Historical context preservation
- Processing status tracking

### Error Handling
- Configurable error tolerance
- Structured error reporting
- Validation error tracking
- Processing error management
- Detailed error logging

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ```

2. Set up environment variables:
   ```bash
   NOVA_INPUT_DIR=path/to/input
   NOVA_OFFICE_ASSETS_DIR=path/to/assets
   NOVA_OFFICE_TEMP_DIR=path/to/temp
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The system uses a combination of:
- Environment variables for paths
- Configuration files for processing rules
- Document handling specifications

Key configuration areas:
- Document processing rules
- Validation requirements
- Error tolerance levels
- Metadata handling
- Logging preferences

## Usage

Process markdown files with embedded documents:

```python
from nova.core.validation import DocumentValidator
from nova.core.config import load_config

# Load configuration
config = load_config('config.yaml')

# Initialize validator
validator = DocumentValidator(config)

# Process files
await validator.validate_input_files(files)
```

### Document Embedding

Nova supports embedding various document types in markdown files:

```markdown
# My Document

Here's an embedded Word document:
[Document Title](path/to/document.docx)<!-- {"embed": true} -->

Here's an embedded PDF with preview:
[PDF Title](path/to/document.pdf)<!-- {"embed": true, "preview": true} -->

Here's an embedded PowerPoint:
[Presentation Title](path/to/slides.pptx)<!-- {"embed": true} -->
```

## Error Handling

The system provides three severity levels:
- CRITICAL: Stops processing
- ERROR: Logged but continues if in lenient mode
- WARNING: Noted but doesn't affect processing

Example error handling:

```python
from nova.core.errors import ErrorHandler, ProcessingError, ErrorSeverity

error_handler = ErrorHandler()

try:
    # Process files
    await validator.validate_input_files(files)
except ProcessingError as e:
    if e.severity == ErrorSeverity.CRITICAL:
        raise
    error_handler.add_error(e)
```

## Logging

Structured logging with:
- Timestamp tracking
- Source identification
- Error details
- Processing status
- Binary content filtering

Example log configuration:

```python
import structlog

logger = structlog.get_logger()
logger.info("processing_started",
    input_files=len(files),
    config=config.model_dump()
)
```

## Environment Variables

Required environment variables:
- `NOVA_INPUT_DIR`: Input directory for markdown files
- `NOVA_OFFICE_ASSETS_DIR`: Directory for document assets
- `NOVA_OFFICE_TEMP_DIR`: Temporary processing directory

Optional variables:
- `NOVA_ERROR_TOLERANCE`: 'strict' or 'lenient' (default: 'lenient')
- `NOVA_LOG_LEVEL`: Logging level (default: 'INFO')

## Development

1. Set up development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements-dev.txt
   ```

2. Run tests:
   ```bash
   pytest tests/
   ```

3. Check code style:
   ```bash
   black src/
   flake8 src/
   mypy src/
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

Please ensure your changes:
- Include appropriate tests
- Follow the existing code style
- Update documentation as needed
- Add entries to CHANGELOG.md

## License

This project is licensed under the MIT License - see the LICENSE file for details.