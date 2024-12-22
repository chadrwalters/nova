# Nova Document Processor

A modern document processing system for parsing, converting, and consolidating markdown files with embedded content support. The system handles various document formats, processes images, and maintains a structured output format while preserving file integrity and managing file sizes efficiently.

## Features

### Core Processing
- Markdown file parsing and processing with markdown-it
- Embedded content handling and conversion
- Image optimization and description generation using AI
- Document format conversion to markdown
- Content consolidation with date-based sorting
- File aggregation with intelligent size management
- Four-phase processing pipeline:
  1. MARKDOWN_PARSE: Initial parsing with size preservation
  2. MARKDOWN_CONSOLIDATE: Content consolidation maintaining integrity
  3. MARKDOWN_AGGREGATE: Efficient file merging with size optimization
  4. MARKDOWN_SPLIT_THREEFILES: Split content into summary, raw notes, and attachments

### Document Support
- **Markdown Files**
  - UTF-8 encoding
  - GFM compatibility
  - Embedded content processing
  - Link maintenance
  - Metadata preservation
  - Size integrity preservation
  - Efficient aggregation
  
- **Images**
  - Format conversion (HEIC → JPG)
  - Size optimization with quality preservation
  - AI-powered description generation
  - Metadata extraction and preservation
  - Cache management for API responses
  - Efficient storage with original preservation
  
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

### File Size Management
- **Phase-Specific Behavior**
  - MARKDOWN_PARSE: Preserves original input file sizes
  - MARKDOWN_CONSOLIDATE: Maintains individual file integrity while adding metadata
  - MARKDOWN_AGGREGATE: Creates single output with size proportional to inputs
  
- **Optimization Features**
  - Intelligent image compression
  - Duplicate content elimination
  - Metadata optimization
  - Cache size management
  - Temporary file cleanup
  
- **Monitoring and Control**
  - Size tracking between phases
  - Anomaly detection and alerts
  - Detailed size statistics
  - Configurable thresholds
  - Automatic cleanup

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

### Output Structure
- **Three-File Organization**
  - `summary.md`: High-level overview and key points
  - `raw_notes.md`: Detailed notes and chronological entries
  - `attachments.md`: Referenced files and metadata
  - Cross-linking between files for easy navigation
  - Consistent structure and formatting
  - Preserved context and relationships

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

The Nova Document Processor uses a carefully organized directory structure to manage input files, processing stages, and final output. All paths are configurable through environment variables.

### Base Structure
```
${NOVA_BASE_DIR}/
├── _NovaInput/              # Source documents and attachments
├── _NovaOutput/             # Final processed output
└── _NovaProcessing/         # Processing workspace
    ├── .state/             # Processing state and tracking
    ├── phases/             # Phase-specific processing
    │   ├── markdown_parse/        # Initial markdown parsing
    │   ├── markdown_consolidate/  # Consolidated output with attachments
    │   ├── markdown_aggregate/    # Single aggregated markdown file
    │   └── markdown_split/        # Three-file split output
    ├── images/             # Image processing workspace
    │   ├── original/      # Original images
    │   ├── processed/     # Optimized images
    │   ├── metadata/      # Image metadata and descriptions
    │   └── cache/         # OpenAI API response cache
    ├── office/            # Office document processing
    │   ├── assets/       # Extracted document assets
    │   └── temp/         # Conversion workspace
    └── temp/              # General temporary files
```

### Directory Purposes

#### Input/Output
- `_NovaInput/`: Place source documents here. Supports markdown files with embedded content, images, and office documents. File sizes are preserved through processing.
- `_NovaOutput/`: Contains the final processed output with converted and optimized content

#### Processing Workspace (`_NovaProcessing/`)
- `.state/`: Tracks processing status, file hashes, modification times, and file size metrics
- `phases/`: Contains phase-specific processing outputs
  - `markdown_parse/`: Initial parsing of markdown and conversion of other formats (preserves original file sizes)
  - `markdown_consolidate/`: Consolidates markdown files with their attachments while maintaining size integrity
  - `markdown_aggregate/`: Combines all consolidated files into a single markdown document with size approximately equal to sum of inputs
  - `markdown_split/`: Splits content into summary, raw notes, and attachments
- `images/`: Handles all image-related processing
  - `original/`: Stores original images in their source format
  - `processed/`: Contains optimized and converted images
  - `metadata/`: Stores image metadata and AI-generated descriptions
  - `cache/`: Caches API responses for image processing
- `office/`: Manages office document processing
  - `assets/`: Stores extracted assets from office documents
  - `temp/`: Temporary workspace for document conversion
- `temp/`: General temporary files that are cleaned up after processing

### Environment Variables

The directory structure is configured through environment variables:
```bash
# Base directories
NOVA_BASE_DIR="/path/to/base"
NOVA_INPUT_DIR="${NOVA_BASE_DIR}/_NovaInput"
NOVA_OUTPUT_DIR="${NOVA_BASE_DIR}/_NovaOutput"
NOVA_PROCESSING_DIR="${NOVA_BASE_DIR}/_NovaProcessing"
NOVA_TEMP_DIR="${NOVA_PROCESSING_DIR}/temp"

# Phase directories
NOVA_PHASE_MARKDOWN_PARSE="${NOVA_PROCESSING_DIR}/phases/markdown_parse"
NOVA_PHASE_MARKDOWN_CONSOLIDATE="${NOVA_PROCESSING_DIR}/phases/markdown_consolidate"
NOVA_PHASE_MARKDOWN_AGGREGATE="${NOVA_PROCESSING_DIR}/phases/markdown_aggregate"
NOVA_PHASE_MARKDOWN_SPLIT="${NOVA_PROCESSING_DIR}/phases/markdown_split"

# Image directories
NOVA_ORIGINAL_IMAGES_DIR="${NOVA_PROCESSING_DIR}/images/original"
NOVA_PROCESSED_IMAGES_DIR="${NOVA_PROCESSING_DIR}/images/processed"
NOVA_IMAGE_METADATA_DIR="${NOVA_PROCESSING_DIR}/images/metadata"
NOVA_IMAGE_CACHE_DIR="${NOVA_PROCESSING_DIR}/images/cache"

# Office directories
NOVA_OFFICE_ASSETS_DIR="${NOVA_PROCESSING_DIR}/office/assets"
NOVA_OFFICE_TEMP_DIR="${NOVA_PROCESSING_DIR}/office/temp"
```

### File Management

- **Input Files**: Place all source files in `_NovaInput/`. The directory structure within input is preserved in the output.
- **Intermediate Files**: All processing artifacts are contained within `_NovaProcessing/` and its subdirectories.
- **Temporary Files**: Automatically cleaned up after processing from the `temp/` directories.
- **Cache Management**: Image processing results are cached in `images/cache/` to avoid redundant API calls.
- **State Tracking**: Processing state is maintained in `.state/` to support incremental processing.

### Best Practices

1. **Input Organization**
   - Keep related files together in subdirectories
   - Use consistent naming conventions
   - Include necessary attachments in the same directory

2. **Output Handling**
   - Treat `_NovaOutput/` as read-only
   - Don't manually modify processed files
   - Use `--force` to regenerate output if needed

3. **Cleanup**
   - Temporary files are automatically managed
   - Cache can be cleared with `--clean-cache`
   - Use `--clean-all` to remove all processing artifacts

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