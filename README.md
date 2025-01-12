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

## Command Line Interface

Nova provides a comprehensive command-line interface for managing your notes and vector store:

### Core Commands

#### `nova process-notes`
Process Bear.app note exports into the system.

```bash
# Process notes from default input directory
nova process-notes

# Process notes from a specific directory
nova process-notes --input-dir /path/to/notes --output-dir /path/to/output
```

Options:
- `--input-dir`: Directory containing Bear.app exports (default: configured input path)
- `--output-dir`: Directory for processed notes (default: .nova/processing)

Error Handling:
- Validates input directory exists
- Creates output directory if missing
- Reports parsing errors with context
- Maintains partial progress on failure

#### `nova process-vectors`
Process text into vector embeddings.

```bash
# Process text from a file
nova process-vectors --text "$(cat document.md)" --output-dir vectors/

# Process text directly
nova process-vectors --text "Your text here" --output-dir vectors/
```

Options:
- `--text`: Input text to process (required)
- `--output-dir`: Directory for vector output (required)

Output Structure:
- `chunk_N.txt`: Text chunks with context
- `embedding_N.npy`: NumPy array embeddings

#### `nova monitor`
Monitor system health and status.

```bash
# Check system health
nova monitor health

# View system statistics
nova monitor stats

# View recent logs
nova monitor logs
nova monitor logs --lines 100  # Show last 100 lines
```

Subcommands:
- `health`: Check system component status
  - .nova directory structure
  - Vector store availability
  - Log system status
- `stats`: Display system statistics
  - Vector embedding count
  - Processed note count
  - Log file count
- `logs`: View recent log entries
  - Options:
    - `--lines`: Number of recent lines to show (default: 50)

### Common Patterns

1. Initial Setup and Health Check:
```bash
# Check system health first
nova monitor health

# Process existing Bear notes
nova process-notes

# Verify processing results
nova monitor stats
```

2. Processing New Content:
```bash
# Process new notes
nova process-notes --input-dir new_notes/

# Check processing status
nova monitor logs
nova monitor stats
```

3. Error Recovery:
```bash
# Check system health
nova monitor health

# View recent errors
nova monitor logs

# Retry processing
nova process-notes
```

### Error Handling

The CLI provides consistent error handling across all commands:

1. Input Validation:
   - Checks for required arguments
   - Validates file/directory paths
   - Verifies input formats

2. Progress Tracking:
   - Real-time progress indicators
   - Operation status updates
   - Completion confirmation

3. Error Reporting:
   - Descriptive error messages
   - Context for failures
   - Recovery suggestions

4. System Status:
   - Health check capabilities
   - Component status verification
   - Resource availability monitoring

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
    - `commands/` - Individual command implementations
      - `process_notes.py` - Bear note processing
      - `process_vectors.py` - Vector store operations
      - `monitor.py` - System monitoring
    - `utils/` - Shared CLI utilities
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
- [x] Command Line Interface
  - [x] Core commands (process-notes, process-vectors, monitor)
  - [x] Rich terminal output with progress tracking
  - [x] Comprehensive error handling
  - [x] System health monitoring
  - [x] Plugin-based architecture
  - [x] Type-safe implementations
  - [x] Test coverage

### In Progress
- [ ] MCP integration
  - [ ] Tool definitions
  - [ ] Context block handling
  - [ ] Transport layer
- [ ] RAG implementation
  - [ ] Query processor
  - [ ] Retrieval system
  - [ ] Result processor

### Planned
- [ ] Monitoring system
  - [ ] FastAPI web app
  - [ ] Metrics collection
  - [ ] Performance tracking
- [ ] Desktop integration
  - [ ] IPC mechanisms
  - [ ] Claude integration
  - [ ] Query interface
