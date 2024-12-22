# Nova Document Processor

A modern document processing system for parsing, converting, and consolidating markdown files with embedded content support. The system handles various document formats, processes images, and maintains a structured output format.

## Features

### Core Processing
- Markdown file parsing and processing with markdown-it
- Embedded content handling and conversion
- Image optimization and description generation
- Document format conversion to markdown
- Content consolidation with date-based sorting

### Document Support
- **Markdown Files**
  - UTF-8 encoding
  - GFM compatibility
  - Embedded content processing
  - Link maintenance
  - Metadata preservation
  
- **Images**
  - Format conversion (HEIC → JPG)
  - Size optimization
  - Quality preservation
  - AI-generated descriptions
  - Metadata extraction
  - Cache management
  
- **Office Documents**
  - Word (.docx, .doc)
    - Text extraction with formatting
    - Paragraph preservation
    - Metadata tracking
    
  - Excel (.xlsx, .xls)
    - Table formatting
    - Header preservation
    - Data type handling
    
  - PowerPoint (.pptx, .ppt)
    - Slide content extraction
    - Notes inclusion
    - Asset preservation
    
  - PDF
    - Text extraction
    - Layout preservation
    - Asset handling
    
  - CSV
    - Encoding detection
    - Table formatting
    - Unicode support

### State Management
- File hash tracking
- Processing status monitoring
- Modification time tracking
- Error state management
- API usage metrics
- Cache invalidation
- Conversion history

### Resource Management
- Temporary file handling
- Cache size control
- Memory usage optimization
- Disk space monitoring
- File encoding management

### Error Handling
- Configurable retry policies
- Error type-specific handling
- Partial success support
- Resource cleanup
- State preservation
- Detailed logging

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Create and configure .env file:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Configuration

The system uses:
- Environment variables for paths and settings
- YAML configuration for processing rules
- State files for tracking progress
- Cache directories for optimization

Key configuration areas:
- Input/output paths
- Processing rules
- OpenAI integration
- Error handling
- Resource limits

## Usage

Basic usage:

```bash
./consolidate.sh              # Process all files
./consolidate.sh --scan      # Show directory structure
./consolidate.sh --force     # Force reprocessing
./consolidate.sh --dry-run   # Show what would be done
```

## Directory Structure

```
nova/
├── input/                    # Source files
├── output/                   # Final output
└── processing/              # Processing workspace
    ├── phases/             # Phase-specific output
    ├── images/             # Image processing
    │   ├── original/      # Original images
    │   ├── processed/     # Optimized images
    │   ├── metadata/      # Image metadata
    │   └── cache/         # API responses
    ├── office/            # Office document processing
    │   ├── assets/       # Extracted assets
    │   └── temp/         # Processing workspace
    └── temp/              # Temporary files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Dependencies

Core dependencies:
- markdown-it-py
- Pillow
- python-docx
- PyMuPDF
- openai
- pydantic
- rich

Development dependencies:
- pytest
- black
- mypy
- ruff