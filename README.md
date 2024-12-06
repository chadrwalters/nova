# Nova Markdown Processing Tools

## Overview

Nova is a Python-based CLI tool for efficient markdown file processing, consolidation, and PDF conversion. It provides robust tools for consolidating multiple markdown files into a single document while preserving images and formatting.

## Features

- **Markdown Consolidation**
  - Multiple file merging with date-based sorting
  - Intelligent image handling and path resolution
  - Support for HEIC/HEIF image conversion
  - Base64 image processing
  - Directory structure preservation
  - Unicode character normalization

- **PDF Generation**
  - Custom HTML template support
  - Configurable CSS styling
  - Automatic image path resolution
  - WeasyPrint integration
  - Memory-efficient processing

- **Image Processing**
  - Automatic image format detection
  - HEIC/HEIF to PNG conversion
  - Path resolution across multiple directories
  - Duplicate image handling
  - Image deduplication via content hashing

## Requirements

- Python 3.11+
- Poetry (Python package manager)
- System dependencies for WeasyPrint 59.0
- pillow-heif for HEIC/HEIF support

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

3. Run the setup script:
   ```bash
   ./setup.sh
   ```
   This will:
   - Install Poetry if not already installed
   - Install project dependencies
   - Set up pre-commit hooks
   - Create necessary directories

4. Activate the Poetry shell:
   ```bash
   poetry shell
   ```

## Usage

### Basic Usage

```bash
# Process markdown files using the consolidate script
./consolidate.sh
```

The script will:
1. Clean up previous output files
2. Create necessary directories
3. Consolidate markdown files from the input directory
4. Process and copy images to the media directory
5. Generate a PDF using the consolidated markdown

### Directory Structure

The script uses the following directory structure:
- `_NovaIndividualMarkdown/`: Source markdown files
- `_NovaConsolidatedMarkdown/`: Consolidated output and media files
- `_Nova/`: Generated PDF files

### Image Support

The tool supports various image formats:
- PNG, JPG, JPEG, GIF, WEBP
- HEIC/HEIF (automatically converted to PNG)
- SVG
- Base64 encoded images

## Development

### Code Style

The project uses:
- Black for code formatting (line length: 88)
- isort for import sorting
- mypy for type checking
- flake8 for linting

### Project Structure

```
src/
├── core/           # Core processing logic
│   ├── markdown_consolidator.py
│   └── markdown_to_pdf_converter.py
├── utils/          # Helper utilities
│   └── colors.py
├── resources/      # Templates and assets
│   └── templates/
│       ├── default.html
│       └── pdf_template.html
└── cli.py         # Command-line interface
```

### Templates

The project includes two HTML templates:
- `default.html`: Basic template with minimal styling
- `pdf_template.html`: Enhanced template with better typography and image handling

## Troubleshooting

### PDF Generation Issues
- Ensure WeasyPrint 59.0 is installed (required for compatibility)
- Check template paths are correct
- Verify media directory permissions
- Check for special characters in filenames

### Image Processing Issues
- Verify HEIC/HEIF support is installed
- Check image file permissions
- Ensure media directory is writable
- Look for image path resolution warnings in output

### Common Solutions
- Run `poetry install` to update dependencies
- Check console output for warning messages
- Verify directory permissions
- Ensure input files use UTF-8 encoding
