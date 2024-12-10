# Nova - Document Processing System

A Python-based document processing system that consolidates markdown files, processes attachments, and generates PDFs while maintaining document relationships and metadata integrity. Supports multiple document formats including Microsoft Office files.

## Core Features

- **Document Processing**
  - Markdown consolidation with metadata preservation
  - Microsoft Office document support (Word, Excel, PowerPoint)
  - PDF generation with WeasyPrint 63.0
  - Media file optimization
  - Document relationship tracking

- **System Features**
  - Structured logging with context
  - Configurable error handling (strict/lenient modes)
  - Progress tracking and reporting
  - Extensible processor architecture
  - Cloud storage compatibility

## Requirements

- Python 3.11+
- Poetry for dependency management
- System dependencies for WeasyPrint 63.0
- libmagic for file type detection
- System libraries for image processing

## Quick Start

1. Install system dependencies:
   ```bash
   # macOS
   brew install python@3.11 libmagic \
       cairo pango gdk-pixbuf libffi

   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install -y \
       python3.11 \
       python3-pip \
       build-essential \
       python3-dev \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf2.0-0 \
       libffi-dev \
       shared-mime-info \
       libmagic1 \
       python3-magic
   ```

2. Clone and setup:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ./setup.sh
   ```

3. Configure environment:
   ```bash
   # Edit .env with your paths
   NOVA_INPUT_DIR="path/to/input"
   NOVA_OUTPUT_DIR="path/to/output"
   NOVA_CONSOLIDATED_DIR="path/to/consolidated"
   NOVA_PROCESSING_DIR="path/to/processing"
   NOVA_MEDIA_DIR="path/to/media"
   ```

4. Run the processor:
   ```bash
   ./consolidate.sh
   ```

## Directory Structure

```
src/
├── cli/                    # Command line interface
│   └── main.py            # CLI implementation
├── core/                   # Core system components
│   ├── config.py          # Configuration management
│   ├── document_consolidator.py
│   ├── document_relationships.py
│   ├── filename_processor.py
│   └── logging.py
├── processors/            # Document processors
│   ├── attachment_processor.py
│   ├── embedded_content_processor.py
│   ├── html_processor.py
│   ├── markdown_processor.py
│   ├── markdown_to_pdf_processor.py
│   └── metadata_processor.py
└── utils/                # Utility functions
```

## Developer Guide

### Adding a New Processor

1. Create a new processor class in `src/processors/`:
   ```python
   from src.core.logging import get_logger
   from src.core.exceptions import ProcessingError

   class NewProcessor:
       def __init__(self, error_tolerance: bool = False):
           self.error_tolerance = error_tolerance
           self.logger = get_logger()

       def process_content(self, content: str) -> str:
           try:
               # Process content
               return processed_content
           except Exception as err:
               self.logger.error("Processing error", exc_info=err)
               if not self.error_tolerance:
                   raise ProcessingError("Failed to process") from err
               return content
   ```

2. Register in `DocumentConsolidator`:
   ```python
   from src.processors.new_processor import NewProcessor

   class DocumentConsolidator:
       def __init__(self, ...):
           self.new_processor = NewProcessor(
               error_tolerance=error_tolerance
           )
   ```

### Error Handling

The system supports two error modes:
```python
# Strict mode - fails on any error
processor = NewProcessor(error_tolerance=False)

# Lenient mode - continues on non-critical errors
processor = NewProcessor(error_tolerance=True)
```

### Logging

Use structured logging with context:
```python
from src.core.logging import get_logger

logger = get_logger()
logger.info("Processing file", 
    file_path=str(file_path),
    processor="markdown",
    phase="consolidation"
)
```

### Document Relationships

Add relationship tracking:
```python
from src.core.document_relationships import DocumentRelationship

relationship = DocumentRelationship(
    source_doc="doc1.md",
    target_doc="doc2.md",
    relationship_type="reference",
    metadata={"section": "introduction"}
)
```

### Processing Pipeline

1. File Analysis:
   ```python
   # Process file metadata
   metadata = metadata_processor.extract_metadata(file_path)
   
   # Process relationships
   relationships = relationship_processor.analyze_file(file_path)
   ```

2. Content Processing:
   ```python
   # Process markdown
   content = markdown_processor.process_file(file_path)
   
   # Process attachments
   attachments = attachment_processor.process_attachments(content)
   
   # Process Office documents
   if file_path.suffix == '.docx':
       content = mammoth.convert_to_html(file_path)
   elif file_path.suffix == '.xlsx':
       df = pandas.read_excel(file_path)
   ```

3. Output Generation:
   ```python
   # Generate HTML
   html = html_processor.process_content(content)
   
   # Generate PDF with WeasyPrint
   HTML(string=html_content).write_pdf(
       output_path,
       stylesheets=[CSS(filename=str(css_path))]
   )
   ```

## Configuration

### Environment Variables

```bash
# Directory Configuration
NOVA_INPUT_DIR          # Source markdown files
NOVA_OUTPUT_DIR         # Generated PDFs
NOVA_CONSOLIDATED_DIR   # Consolidated output
NOVA_PROCESSING_DIR     # Processing workspace
NOVA_MEDIA_DIR         # Media files

# Processing Options
NOVA_ERROR_TOLERANCE    # strict/lenient
PDF_TIMEOUT            # PDF generation timeout
PDF_CHUNK_SIZE         # Processing chunk size
```

### Processing Options

```python
from src.core.config import ProcessingConfig

config = ProcessingConfig(
    input_dir=Path("input"),
    output_dir=Path("output"),
    consolidated_dir=Path("consolidated"),
    processing_dir=Path("processing"),
    media_dir=Path("media"),
    error_tolerance="lenient"
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass:
   ```bash
   ./run_tests.sh
   ```
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.