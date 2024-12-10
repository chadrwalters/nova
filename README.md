# Nova Document Processor

A robust Python CLI tool for markdown file consolidation and PDF generation with advanced document processing capabilities.

## Features

### Core Processing
- Asynchronous markdown to HTML conversion
- Smart document consolidation with state tracking
- PDF generation with customizable templates
- Phased processing with checkpointing
- Resource-aware processing with automatic cleanup

### Document Handling
- Metadata extraction and preservation
- Attachment processing
- Image optimization and embedding
- Cross-document referencing
- Document relationship tracking

### Advanced Features
- Progress tracking and state management
- Error recovery with configurable retry logic
- Resource monitoring and management
- Structured logging with context
- Phase-based processing control

## Requirements

- Python 3.11+
- Poetry for dependency management
- wkhtmltopdf for PDF generation
- Git for version control

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

### Advanced Usage
```bash
# Process specific phases
poetry run python -m src.cli.main process \
    --phase HTML_INDIVIDUAL \
    --processing-dir "path/to/processing"

# Force reprocessing of all files
poetry run python -m src.cli.main process --force
```

## Configuration

### Environment Variables
Create a `.env` file with:
```env
NOVA_INPUT_DIR=/path/to/input
NOVA_OUTPUT_DIR=/path/to/output
NOVA_PROCESSING_DIR=/path/to/processing
```

### Processing Phases
- HTML_INDIVIDUAL: Convert individual markdown files to HTML
- MARKDOWN_CONSOLIDATED: Combine markdown files
- HTML_CONSOLIDATED: Generate consolidated HTML
- PDF: Create final PDF output
- ALL: Execute complete pipeline

## Directory Structure

```
project/
├── input/          # Source markdown files
├── output/         # Generated PDFs
└── processing/     # Intermediate files
    ├── markdown/   # Processed markdown
    ├── html/       # Generated HTML
    ├── media/      # Processed images
    └── attachments/# Processed attachments
```

## Error Handling

The processor implements robust error handling with:
- Automatic retries for transient failures
- State preservation during processing
- Detailed error logging
- Resource cleanup on failure
- Configurable error tolerance

## Resource Management

- Automatic memory monitoring
- Disk space management
- File locking for concurrent access
- Temporary file cleanup
- Resource usage logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Project Structure