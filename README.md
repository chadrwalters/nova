# Nova Document Processor

A Python CLI tool for markdown file consolidation and PDF generation.

## Features

- Markdown to HTML conversion with Python-Markdown
- HTML processing with BeautifulSoup4
- PDF generation with PyMuPDF (fitz)
- Image and attachment handling
- Document metadata processing
- Configurable styling and templates

## Requirements

- Python 3.11+
- Poetry for dependency management
- System dependencies for PyMuPDF
- Git for version control

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nova.git
cd nova
```

2. Install dependencies with Poetry:
```bash
poetry install
```

## Usage

```bash
# Process markdown files and generate PDF
./consolidate.sh

# Or run directly with Poetry
poetry run python -m src.cli.main process path/to/input path/to/output
```

## Configuration

Configuration is managed through environment variables and `.env` files:

```env
NOVA_INPUT_DIR=/path/to/input
NOVA_OUTPUT_DIR=/path/to/output
NOVA_PROCESSING_DIR=/path/to/processing
```

## PDF Generation

The tool uses PyMuPDF (fitz) for PDF generation, which provides:
- Fast and efficient PDF creation
- HTML to PDF conversion
- Image and media handling
- Custom styling support
- Document metadata

## Development

1. Set up development environment:
```bash
poetry install
pre-commit install
```

2. Run tests:
```bash
poetry run pytest
```

3. Format code:
```bash
poetry run black src tests
poetry run isort src tests
```

## Project Structure

```
nova/
├── src/
│   ├── cli/           # Command line interface
│   ├── core/          # Core functionality
│   ├── processors/    # Document processors
│   ├── resources/     # Templates and styles
│   └── utils/         # Utility functions
├── tests/             # Test files
├── .env              # Environment variables
└── pyproject.toml    # Project configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
