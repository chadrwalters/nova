# Nova

![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)

Nova is an AI-powered note processing and search system that provides semantic search capabilities through vector embeddings and MCP integration.

## Prerequisites

- Python 3.11 or higher
- uv package manager (`pip install uv`)
- Cursor IDE for Claude integration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/chadwalters/nova.git
cd nova
```

2. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install the package:
```bash
uv pip install -e .
```

## Initial Setup

1. Create required directories:
```bash
mkdir -p .nova/vectors .nova/logs .nova/metrics
```

2. Configure input directory:
```bash
# Default path (recommended):
mkdir -p ~/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput

# Or set custom path in .env:
echo "NOVA_INPUT=/path/to/your/input/dir" > .env
```

## Usage

### Command Order and Flow

1. Start MCP Server (Required for all operations):
```bash
uv run python -m nova.cli mcp-server
```

2. Process Notes:
```bash
# From default input directory
uv run python -m nova.cli process-notes

# From custom directory
uv run python -m nova.cli process-notes --input-dir /path/to/notes
```

3. Monitor System (Optional but recommended):
```bash
# Check system health
uv run python -m nova.cli monitor health

# View detailed statistics
uv run python -m nova.cli monitor stats --verbose

# Check for warnings
uv run python -m nova.cli monitor warnings

# View logs
uv run python -m nova.cli monitor logs
```

4. Search Notes:
```bash
# Basic search
uv run python -m nova.cli search "your query here"

# Search with tag filter
uv run python -m nova.cli search "your query" --tag work

# Search with date filter
uv run python -m nova.cli search "your query" --after 2024-01-01
```

### System Health Monitoring

The monitoring system tracks:

1. Memory Usage:
   - Current usage and peak memory
   - Warning thresholds
   - Usage trends

2. Vector Store Health:
   - Document count and statistics
   - Chunk distribution
   - Embedding performance
   - Cache hit rates

3. Directory Health:
   - Space utilization
   - Permissions
   - Structure integrity

4. Performance Metrics:
   - Search response times
   - Processing speeds
   - Error rates

## Development

### Running Tests
```bash
# Type checking (must pass before tests)
uv run mypy src/nova

# Run all tests
uv run pytest -v

# Run linting
uv run ruff src/nova
```

### Building Documentation
```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Build docs
uv run mkdocs build
```

## Project Structure

```
.nova/              # System directory (all system files MUST be here)
├── vectors/        # Vector store data
├── logs/          # System logs
└── metrics/       # Performance metrics

src/nova/          # Source code
├── cli/           # Command line interface
├── vector_store/  # Vector storage and search
├── monitoring/    # System monitoring
└── examples/      # Example scripts
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Getting Started](docs/getting-started.md) - Detailed setup guide
- [User Guide](docs/user-guide/) - Usage instructions and examples
- [Architecture](docs/architecture/) - System design and components
- [API Reference](docs/api/) - API documentation
- [Development](docs/development/) - Development guide

## Troubleshooting

1. If the MCP server fails to start:
   - Check if port 8765 is available
   - Verify .nova directory exists and is writable
   - Check logs at .nova/logs/nova.log

2. If vector search fails:
   - Ensure notes have been processed first
   - Check vector store health: `uv run python -m nova.cli monitor health`
   - Verify ChromaDB is working: `uv run python -m nova.cli monitor stats`

3. For other issues:
   - Check logs: `uv run python -m nova.cli monitor logs`
   - Run health check: `uv run python -m nova.cli monitor health --verbose`
   - Verify system requirements are met
