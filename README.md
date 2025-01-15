# Nova

A vector-based note processing and search system with MCP integration.

## Requirements

- Python 3.11+
- uv package manager (pip/python usage is FORBIDDEN)
- python-magic (for format detection)
- html2text (for HTML conversion)
- docutils (for RST conversion)

## File System Organization

All system files are stored in the `.nova` directory:
- `.nova/processing/`: Processed notes
- `.nova/vectors/`: Vector store database
- `.nova/logs/`: System logs

Input files location is configurable:
- Default: `/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput`
- Can be overridden via command line arguments

## Testing

- All tests MUST run through uv: `uv run pytest -v`
- Type checking MUST be run before tests
- Tests should run without approval
- Test command: `uv run pytest -v`

## Installation

1. Create a Python virtual environment:
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
Process notes with automatic format detection and conversion.

```bash
# Process notes from default input directory
uv run nova process-notes

# Process notes from a specific directory
uv run nova process-notes --input-dir /path/to/notes --output-dir /path/to/output
```

Options:
- `--input-dir`: Directory containing notes (default: configured input path)
- `--output-dir`: Directory for processed notes (default: .nova/processing)

Supported Formats:
- Text Formats:
  - Markdown (.md) - Native format
  - Plain text (.txt) - Direct conversion
  - HTML (.html, .htm) - via html2text
  - reStructuredText (.rst) - via docutils
  - AsciiDoc (.adoc, .asciidoc) - via asciidoc
  - Org Mode (.org) - via pandoc
  - Wiki (.wiki) - via pandoc
  - LaTeX (.tex) - via pandoc
- Office Formats:
  - Word (.docx) - via pandoc
  - Excel (.xlsx) - via pandoc
  - PowerPoint (.pptx) - via pandoc
- Other Formats:
  - PDF (.pdf) - via pandoc

#### `nova process-bear-vectors`
Process Bear notes into vector embeddings.

```bash
# Process notes from default input directory
uv run nova process-bear-vectors --input-dir /path/to/notes --output-dir .nova/vectors

# Process notes from a specific directory
uv run nova process-bear-vectors --input-dir /path/to/notes --output-dir /path/to/vectors
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

#### `nova search`
Search through vector embeddings using sentence-transformers for semantic similarity.

```bash
# Search with default settings
uv run nova search "your search query"

# Search with custom parameters
uv run nova search "your search query" --vector-dir /path/to/vectors --limit 10
```

Options:
- `--vector-dir`: Directory containing vector store (default: .nova/vectors)
- `--limit`: Maximum number of results to return (default: 5)

Output:
- Ranked list of similar notes with:
  - Title and normalized similarity score (0-100%)
  - Tags and creation date
  - Content preview (first 200 characters)

#### `nova clean-processing`
Clean the processed notes directory.

```bash
# Show warning without deleting
uv run nova clean-processing

# Force deletion of processed notes
uv run nova clean-processing --force
```

Options:
- `--force`: Force deletion without confirmation

#### `nova clean-vectors`
Clean the vector store.

```bash
# Show warning without deleting
uv run nova clean-vectors

# Force deletion of vector store
uv run nova clean-vectors --force
```

Options:
- `--force`: Force deletion without confirmation

#### `nova monitor`
Monitor system health and status.

```bash
# Check system health
uv run nova monitor health

# View system statistics
uv run nova monitor stats

# View recent logs
uv run nova monitor logs
```

Subcommands:
- `health`: Check system component status
- `stats`: Display system statistics
- `logs`: View recent log entries

## MCP Integration

Nova runs an MCP server on port 8765 for Claude Desktop integration. This port was chosen to avoid conflicts with common development services.

IMPORTANT: The MCP server is READ-ONLY for the vector store. All write operations (processing notes, creating vectors, cleaning) must be done through the CLI commands. This ensures data integrity and proper processing of notes.

MCP Server Capabilities:
- Search existing vectors
- Retrieve note content
- Monitor system health
- View statistics

Write Operations (CLI Only):
- Processing notes
- Creating vectors
- Cleaning vectors/processing
- System maintenance
