# Nova Document Processor

A modern, async document processing pipeline for converting markdown to PDF with advanced styling and security features.

## Features

- Markdown to PDF conversion using markdown-it and WeasyPrint
- GitHub-style formatting
- Metadata extraction and processing
- Secure content validation
- Configurable styling and output options
- Async processing pipeline
- Structured logging

### Document Processing Features

- **Word Documents (.docx, .doc)**
  - Full text extraction with formatting
  - Image preservation
  - Metadata extraction (author, title, dates)
  - Table conversion to markdown
  
- **PDF Documents (.pdf)**
  - Text extraction with layout preservation
  - Image extraction
  - OCR support (optional)
  - Metadata preservation
  - Page-by-page processing
  
- **PowerPoint Presentations (.pptx, .ppt)**
  - Slide text extraction
  - Speaker notes support
  - Image extraction
  - Slide separation with customizable markers
  - Metadata preservation

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ```

2. Run the installation script:
   ```bash
   ./install.sh
   ```

   This will:
   - Install Poetry if not already installed
   - Create necessary directories
   - Set up environment variables
   - Install Python dependencies
   - Install system dependencies (macOS/Linux)

3. Verify the installation:
   ```bash
   poetry run nova --version
   ```

## Configuration

Nova uses a YAML configuration file for customization. The default configuration is installed at `$NOVA_CONFIG_DIR/default_config.yaml`:

```yaml
document_handling:
  word_processing:
    extract_images: true
    preserve_formatting: true
    table_handling: markdown
    image_output_dir: "assets/images"
    
  pdf_processing:
    extract_images: true
    ocr_enabled: true
    
  powerpoint_processing:
    extract_images: true
    include_notes: true
    slide_separator: "---"
```

## Usage

1. Basic document processing:
   ```bash
   poetry run nova process --input input_dir --output output_dir
   ```

2. Process with custom configuration:
   ```bash
   poetry run nova process --input input_dir --output output_dir --config config.yaml
   ```

3. Process with custom assets directory:
   ```bash
   poetry run nova process --input input_dir --output output_dir --assets assets_dir
   ```

## Document Embedding

Nova supports embedding various document types in markdown files:

```markdown
# My Document

Here's an embedded Word document:
[Document Title](path/to/document.docx) <!-- {"embed": true, "extract_images": true} -->

Here's an embedded PDF:
[PDF Title](path/to/document.pdf) <!-- {"embed": true, "ocr": true} -->

Here's an embedded PowerPoint:
[Presentation Title](path/to/slides.pptx) <!-- {"embed": true, "include_notes": true} -->
```

## Environment Variables

The following environment variables are set up by the installation script:

- `NOVA_BASE_DIR`: Base directory for Nova (default: ~/Documents/Nova)
- `NOVA_INPUT_DIR`: Input directory for markdown files
- `NOVA_OUTPUT_DIR`: Output directory for processed files
- `NOVA_CONFIG_DIR`: Configuration directory
- `NOVA_PROCESSING_DIR`: Directory for processing artifacts
- `NOVA_OFFICE_ASSETS_DIR`: Directory for extracted assets
- `NOVA_OFFICE_TEMP_DIR`: Temporary directory for processing
- `NOVA_PHASE_MARKDOWN_PARSE`: Output directory for parsed markdown
- `NOVA_PHASE_MARKDOWN_CONSOLIDATE`: Output directory for consolidated markdown
- `NOVA_PHASE_PDF_GENERATE`: Output directory for generated PDFs

## Development

1. Set up development environment:
   ```bash
   poetry install --with dev
   ```

2. Run tests:
   ```bash
   poetry run pytest tests/
   ```

3. Check code style:
   ```bash
   poetry run black src/
   poetry run flake8 src/
   poetry run mypy src/
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.