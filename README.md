# Nova

A RAG-based system for Bear.app notes with MCP integration.

## Requirements

- Python 3.10
- uv package manager (pip usage is forbidden)
- EasyOCR (for text extraction)

## Installation

1. Create a Python 3.10 virtual environment:
```bash
uv venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
uv pip install -e .
```

3. Install pre-commit hooks:
```bash
uv pip install pre-commit
uv run pre-commit install
```

## Project Structure

- `src/nova/` - Main package directory
  - `bear_parser/` - Bear note parsing functionality
    - `parser.py` - Contains BearParser, BearNote, and BearAttachment classes
    - `ocr.py` - EasyOCR-based text extraction
    - `exceptions.py` - Custom exception hierarchy
  - `vector_store/` - Vector store functionality
    - `chunking.py` - Heading-aware document chunking
    - `embedding.py` - Text embedding with caching
  - `cli/` - Command-line interface modules
    - `generate_metadata.py` - Generates metadata.json for Bear notes
    - `process_notes.py` - Processes Bear notes using the parser
    - `process_vectors.py` - Standalone vector store processing
    - `process_bear_vectors.py` - Bear note vector store integration
- `.nova/` - System directory for processing files, logs, and placeholders
  - `placeholders/ocr/` - OCR failure placeholders
  - `processing/ocr/` - OCR processing files
  - `vector_store/` - Vector embeddings and cache
  - `logs/` - System logs

## Usage

### Processing Bear Notes

1. Configure input directory:
Default: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`

2. Generate metadata for your Bear notes:
```bash
nova generate-metadata
```
This creates a metadata.json file containing:
- Note creation/modification dates
- Attachment references
- Initial tag list

3. Process the notes:
```bash
nova process-notes
```
This will:
- Parse all notes in the configured input directory
- Extract tags (including nested #tag/subtag format)
- Process any image attachments using OCR
- Generate placeholders for failed OCR attempts
- Create a structured output in the .nova directory

### Vector Store Processing

1. Process standalone text:
```bash
nova process-vectors "Your text here" output_directory
```
This demonstrates:
- Heading-aware document chunking
- Semantic content splitting
- Embedding generation with caching
- Structured output:
  - chunk_N.txt: Text chunks with context
  - embedding_N.npy: NumPy array embeddings

2. Process Bear notes with vector store:
```bash
nova process-bear-vectors input_directory output_directory
```
This integrates:
- Bear note parsing with metadata
- Tag-aware chunking
- Heading context preservation
- Per-note organization:
  - note_title/chunk_N.txt
  - note_title/embedding_N.npy

### Configuration

Default paths:
- Input directory: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`
- System directory: `.nova/`

### OCR Processing

The system uses EasyOCR for processing images with the following features:
- Multiple OCR configurations for quality/speed tradeoff
- Confidence threshold validation (50%)
- Automatic fallback for low confidence results
- JSON-based placeholder format for failed OCR
- 30-day retention policy with automatic cleanup

## Development

Run tests:
```bash
uv run pytest -v
```

Run pre-commit checks:
```bash
uv run pre-commit run --all-files
```

Pre-commit configuration:
- Type checking with mypy
- Code formatting with ruff
- Security checks with bandit
- Docstring formatting
- Python 3.10+ compatibility

## Implementation Status

### Completed
- [x] Bear note parsing
- [x] Metadata generation
- [x] Tag extraction (with code block awareness)
- [x] OCR infrastructure
- [x] Error handling system
- [x] Placeholder management
- [x] Vector store implementation
  - [x] Chunking engine with heading awareness
  - [x] Embedding pipeline with caching
  - [x] Bear note integration
  - [x] CLI modules for processing

### In Progress
- [ ] MCP integration
- [ ] RAG implementation

### Planned
- [ ] Monitoring system
