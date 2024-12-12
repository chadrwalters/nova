# Nova Document Processor

A sophisticated document processing pipeline for converting, consolidating, and formatting documents with a focus on PDF output optimization.

## Features

- Multi-phase document processing pipeline
- Structured metadata handling
- Advanced PDF layout and formatting
- Resource-aware processing
- Robust error handling and validation
- Support for multiple document formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nova.git
cd nova
```

2. Install system dependencies:
```bash
# macOS
brew install wkhtmltopdf

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y wkhtmltopdf
```

3. Install Python dependencies:
```bash
poetry install
```

## Usage

### Basic Usage
```bash
# Using the convenience script
./consolidate.sh

# Direct CLI usage
poetry run python -m src.cli.main consolidate \
    --input-dir "path/to/input" \
    --output-dir "path/to/output" \
    --processing-dir "path/to/processing" \
    --template-dir "src/resources/templates"
```

## Pipeline Phases

The processor operates in distinct phases:

1. **HTML_INDIVIDUAL**
   - Converts individual markdown files to HTML
   - Validates input markdown
   - Processes embedded content
   - Handles image references
   - Preserves metadata

2. **MARKDOWN_CONSOLIDATED**
   - Combines markdown files
   - Maintains document order
   - Preserves headers
   - Handles cross-references
   - Updates internal links

3. **HTML_CONSOLIDATED**
   - Applies HTML template
   - Processes consolidated markdown
   - Handles resource paths
   - Updates internal references

4. **PDF**
   - Applies PDF template
   - Processes images
   - Sets metadata
   - Note: Headers and footers in wkhtmltopdf are explicitly forbidden

## Configuration

### Environment Variables
Create a `.env` file with:
```env
NOVA_INPUT_DIR=/path/to/input
NOVA_OUTPUT_DIR=/path/to/output
NOVA_PROCESSING_DIR=/path/to/processing
```

### Style Configuration
The default configuration (`config/default_config.yaml`) supports:

```yaml
style:
  page_size: 'A4'
  margin: '0.5in'
  font_family: 'Arial'
  font_size: '11pt'
  line_height: '1.5'
  colors:
    text: '#333333'
    headings: '#000000'
    links: '#0066cc'
```

## Document Metadata

Documents support rich metadata:
- Title
- Date
- Author
- Category
- Tags
- Summary
- Status
- Priority
- Keywords
- References
- Related documents
- Custom fields

## Error Handling

The processor implements comprehensive error handling:
- Retry policies with exponential backoff
- State tracking and recovery
- Partial success handling
- Resource cleanup
- Detailed logging with binary content filtering

## Resource Management

- File operations using pathlib.Path
- Memory usage monitoring
- Disk space management
- Proper file locking
- Temporary file cleanup
- Streaming for large files

## Code Quality

- Black formatter (max line length: 88)
- Type hints with strict mypy
- Google style docstrings
- Comprehensive test coverage

## Project Structure
```
nova/
├── src/
│   ├── core/
│   │   ├── types.py           # Core data types
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── validation.py      # Input validation
│   │   └── logging.py         # Logging configuration
│   ├── processors/
│   │   ├── markdown_processor.py
│   │   ├── html_processor.py
│   │   ├── pdf_processor.py
│   │   └── word_processor.py
│   └── resources/
│       └── templates/         # HTML/PDF templates
├── config/
│   └── default_config.yaml    # Default configuration
├── tests/                     # Test suite
├── consolidate.sh            # Convenience script
└── pyproject.toml           # Project dependencies
```

## Dependencies

Key dependencies (from pyproject.toml):
- Python ^3.10
- markdown ^3.5.1
- pdfkit ^1.0.0
- structlog ^23.2.0
- PyPDF2 ^3.0.1
- python-docx ^0.8.11
- python-pptx ^0.6.21

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## License

MIT License - See LICENSE file for details