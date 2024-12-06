# Nova Markdown Processing Tools

## Overview

Nova is a Python-based CLI tool for efficient markdown file processing, consolidation, and PDF conversion. It provides robust tools for converting between markdown and PDF formats while maintaining document structure and styling.

## Features

- **Markdown to PDF Conversion**
  - Custom template support
  - Configurable CSS styling
  - Image processing and optimization
  - Memory-efficient chunk processing for large documents
  - Async processing capabilities

- **PDF to Markdown Conversion**
  - Clean text extraction
  - Structure preservation
  - Basic formatting conversion

- **Markdown Consolidation**
  - Multiple file merging
  - Directory structure preservation
  - Image handling and optimization
  - Base64 content processing

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/chadwalt/nova.git
   cd nova
   ```

2. Install system dependencies:

   On macOS:
   ```bash
   brew install python@3.11
   ```

   On Ubuntu/Debian:
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       python3.11 \
       python3-pip \
       build-essential \
       python3-dev \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf2.0-0 \
       libffi-dev \
       shared-mime-info
   ```

   On Windows:
   - Install Python 3.11+ from python.org
   - Install the required system libraries for WeasyPrint

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment:
   ```bash
   cp .env.template .env
   ```

## Usage

### Converting Markdown to PDF

```bash
# Basic conversion
python -m src.cli convert md-to-pdf --input input.md --output output.pdf

# With custom template
python -m src.cli convert md-to-pdf --input input.md --output output.pdf --template custom.html

# With custom styling
python -m src.cli convert md-to-pdf --input input.md --output output.pdf --style custom.css
```

### Converting PDF to Markdown

```bash
# Basic conversion
python -m src.cli convert pdf-to-md --input input.pdf --output output.md

# With media directory for extracted content
python -m src.cli convert pdf-to-md --input input.pdf --output output.md --media-dir ./media
```

### Consolidating Markdown Files

```bash
# Basic consolidation
python -m src.cli consolidate --input-dir ./docs --output-file output.md

# With image optimization
python -m src.cli consolidate --input-dir ./docs --output-file output.md --optimize-images
```

## Project Structure

```
src/
├── core/
│   ├── markdown_to_pdf_converter.py
│   ├── pdf_to_markdown_converter.py
│   └── markdown_consolidator.py
├── utils/
│   ├── colors.py
│   └── timing.py
├── resources/
│   ├── templates/
│   ├── styles/
│   └── prompts/
└── cli/
```

## Configuration

### Environment Variables

- `NOVA_CONSOLIDATED_DIR`: Directory for consolidated markdown files
- `PDF_TIMEOUT`: Timeout for PDF generation (default: 300 seconds)
- `PDF_CHUNK_SIZE`: Size of chunks for processing large files (in MB)

### Customization

- Templates: Add custom HTML templates in `src/resources/templates/`
- Styles: Add custom CSS files in `src/resources/styles/`
- Configuration: Modify default settings in `config/default_config.yaml`

## Dependencies

### Core Dependencies
- Python 3.11+
- WeasyPrint (PDF generation)
- Click (CLI interface)
- Rich (console output)
- Pillow (image processing)
- PyPDF (PDF processing)
- BeautifulSoup4 (HTML processing)
- Jinja2 (template rendering)
- PyYAML (configuration)

## Troubleshooting

### PDF Generation Issues
- Check available memory for large documents
- Increase PDF_TIMEOUT for complex documents
- Verify template and style file paths
- Check file permissions

### Image Processing Issues
- Verify image file permissions
- Check available memory for large images
- Ensure media directory is writable

### General Issues
- Check console output for error messages
- Verify all dependencies are installed
- Confirm sufficient disk space
- Check file permissions
