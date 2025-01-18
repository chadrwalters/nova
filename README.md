# Nova

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

2. Configure input directory (default: ~/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput):
```bash
# Either create default directory:
mkdir -p ~/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput

# Or set custom path in .env:
echo "NOVA_INPUT=/path/to/your/input/dir" > .env
```

## Usage

### Basic Commands

```bash
# Process notes from input directory
nova process-notes --input-dir $NOVA_INPUT

# Search through processed notes
nova search "your query here"

# Monitor system health
nova monitor health
nova monitor stats
nova monitor logs
```

### MCP Server Setup

1. Start the MCP server:
```bash
nova mcp-server
```
The server will start on http://127.0.0.1:8765

2. Verify server health:
```bash
curl http://127.0.0.1:8765/health
```

### Claude Integration in Cursor

1. Open Cursor IDE
2. Start a new conversation with Claude
3. The Nova MCP server will be automatically detected
4. You can now use commands like:
   - Search through your notes
   - Monitor system health
   - Process new documents
   - View logs and metrics

## Development

### Running Tests
```bash
# Run all tests
uv run pytest -v

# Run type checking
uv run mypy src/nova

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
.nova/              # System directory
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
   - Ensure notes have been processed
   - Check vector store health with `nova monitor health`
   - Verify ChromaDB is working correctly

3. For other issues:
   - Check the logs: `nova monitor logs`
   - Run health check: `nova monitor health`
   - Verify system requirements are met
