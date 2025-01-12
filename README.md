# Nova

A RAG-based system for Bear.app notes with MCP integration.

## Requirements

- Python 3.10
- uv package manager
- Tesseract OCR (for image processing)
- EasyOCR (for text extraction)

## Installation

1. Install Tesseract:
```bash
brew install tesseract
```

2. Create a Python 3.10 virtual environment:
```bash
uv venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
uv pip install -e .
```

## Project Structure

- `src/nova/` - Main package directory
  - `bear_parser/` - Bear note parsing functionality
    - `parser.py` - Contains BearParser, BearNote, and BearAttachment classes
    - `exceptions.py` - Custom exception hierarchy
- `scripts/` - Utility scripts
  - `generate_metadata.py` - Generates metadata.json for Bear notes
  - `process_notes.py` - Processes Bear notes using the parser
- `.nova/` - System directory for processing files, logs, and placeholders
  - `placeholders/ocr/` - OCR failure placeholders
  - `processing/` - Temporary processing files
  - `logs/` - System logs

## Usage

### Processing Bear Notes

1. Configure input directory:
Default: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`

2. Generate metadata for your Bear notes:
```bash
uv run python scripts/generate_metadata.py
```
This creates a metadata.json file containing:
- Note creation/modification dates
- Attachment references
- Initial tag list

3. Process the notes:
```bash
uv run python scripts/process_notes.py
```
This will:
- Parse all notes in the configured input directory
- Extract tags (including nested #tag/subtag format)
- Process any image attachments using OCR
- Generate placeholders for failed OCR attempts
- Create a structured output in the .nova directory

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

## Implementation Status

### Completed
- [x] Bear note parsing
- [x] Metadata generation
- [x] Tag extraction (with code block awareness)
- [x] OCR infrastructure
- [x] Error handling system
- [x] Placeholder management

### In Progress
- [ ] Vector store implementation
- [ ] Chunking engine
- [ ] Embedding pipeline

### Planned
- [ ] MCP integration
- [ ] RAG implementation
- [ ] Desktop client
- [ ] Monitoring system
