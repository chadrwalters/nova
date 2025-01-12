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

#### `nova process-bear-vectors`
Process Bear notes into vector embeddings.

```bash
# Process notes from default input directory
nova process-bear-vectors --input-dir /path/to/notes --output-dir .nova/vectors

# Process notes from a specific directory
nova process-bear-vectors --input-dir /path/to/notes --output-dir /path/to/vectors
```

Options:
- `--input-dir`: Directory containing Bear notes (required)
- `--output-dir`: Directory for vector store (required)

Output:
- Vector embeddings stored in Chroma database
- Metadata preserved with each embedding:
  - Source file path
  - Note title
  - Creation date
  - Tags

#### `nova clean-vectors`
Clean the vector store.

```bash
# Show warning without deleting
nova clean-vectors

# Force deletion of vector store
nova clean-vectors --force
```

Options:
- `--force`: Force deletion without confirmation

Warning:
- This command deletes the entire vector store
- Operation cannot be undone
- Requires explicit --force flag

#### `nova monitor`
Monitor system health and status.

```bash
# Check system health
nova monitor health

# View system statistics
nova monitor stats

# View recent logs
nova monitor logs
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
- `logs`: View recent log entries (last 50 lines)

### Common Patterns

1. Initial Setup and Health Check:
```bash
# Check system health first
nova monitor health

# Process existing Bear notes
nova process-notes

# Create vector embeddings
nova process-bear-vectors --input-dir /path/to/notes --output-dir .nova/vectors

# Verify processing results
nova monitor stats
```

2. Processing New Content:
```bash
# Clean existing vectors if needed
nova clean-vectors --force

# Process new notes
nova process-notes --input-dir new_notes/

# Create new vector embeddings
nova process-bear-vectors --input-dir new_notes/ --output-dir .nova/vectors

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

# Clean vectors if corrupted
nova clean-vectors --force

# Retry processing
nova process-notes
nova process-bear-vectors --input-dir /path/to/notes --output-dir .nova/vectors
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
  - `ingestion/` - Note ingestion functionality
    - `bear/` - Bear note parsing
      - `__init__.py` - Contains BearParser and BearNote classes
  - `vector_store/` - Vector store functionality
    - `chunking.py` - Heading-aware document chunking
    - `embedding.py` - Text embedding with caching
    - `store.py` - Chroma-based vector store
  - `cli/` - Command-line interface modules
    - `commands/` - Individual command implementations
      - `process_notes.py` - Bear note processing
      - `process_bear_vectors.py` - Vector store operations
      - `clean_vectors.py` - Vector store cleanup
      - `monitor.py` - System monitoring
    - `utils/` - Shared CLI utilities
- `.nova/` - System directory
  - `processing/` - Processed notes with metadata
  - `vectors/` - Vector embeddings (Chroma DB)
  - `logs/` - System logs

## Usage

### Processing Bear Notes

1. Configure input directory:
Default: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`

2. Process the notes:
```bash
nova process-notes
```
This will:
- Parse all notes in the configured input directory
- Extract metadata (title, date, tags)
- Create a structured output in .nova/processing

### Vector Store Processing

1. Process Bear notes with vector store:
```bash
nova process-bear-vectors --input-dir /path/to/notes --output-dir .nova/vectors
```
This creates:
- Vector embeddings for each note
- Metadata including:
  - Note title and date
  - Tags
  - Source file path

2. Clean vector store if needed:
```bash
nova clean-vectors --force
```
Use this when:
- Starting fresh
- Fixing corrupted vectors
- Changing embedding models

### Configuration

Default paths:
- Input directory: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`
- System directory: `.nova/`
  - Processing: `.nova/processing/`
  - Vectors: `.nova/vectors/`
  - Logs: `.nova/logs/`

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
  - [x] Core commands (process-notes, process-bear-vectors, monitor)
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
