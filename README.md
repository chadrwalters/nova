# Nova Document Processor - Markdown Parse Phase

A modern document processing system for parsing and validating markdown files with embedded document support.

## Features

### Core Processing
- Markdown file processing and validation
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
from nova.processors.markdown_processor import MarkdownProcessor

# Load configuration
config = load_config()

# Initialize processor
processor = MarkdownProcessor(config)

# Process a file or directory
processor.process_file("path/to/document.md")
processor.process_directory("path/to/documents/")
```

## Contributing

Contributions are welcome! Please read our contributing guidelines first.

Please ensure your changes:
- Include appropriate tests
- Follow the existing code style
- Update documentation as needed
- Add entries to CHANGELOG.md

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Dependencies

- markdown-it-py for markdown processing
- markitdown for document conversion

## Image Processing

The system handles various image formats including HEIC files. Images are:
- Converted to standard formats if needed
- Optimized for size and quality
- Given AI-generated descriptions when possible
- Tracked with detailed metadata

## Office Document Processing

Supports various office document formats:
- PDF files
- Microsoft Office documents (docx, xlsx, pptx)
- Legacy Office formats (doc, xls, ppt)

Documents are converted to markdown with:
- Preserved formatting where possible
- Extracted images and assets
- Detailed metadata and technical information
- Fallback content when conversion fails