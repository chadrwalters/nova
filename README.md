# Nova CLI

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A command-line tool for consolidating Markdown files and uploading them to Graphlit.

## Features

- **Consolidate Markdown**: Process and consolidate Markdown files from a source directory
- **Upload to Graphlit**: Upload Markdown files to Graphlit with a single command
- **Unified Configuration**: Use a single TOML configuration file for all commands
- **Structured Logging**: Comprehensive logging with configurable levels
- **Dry Run Mode**: Test upload functionality without making actual API calls

## Installation

```bash
# Using UV (recommended)
uv pip install nova

# Using pip
pip install nova
```

## Quick Start

### 1. Create Configuration File

Create a unified configuration file by copying the template:

```bash
cp nova.toml.template nova.toml
```

Edit the `nova.toml` file with your specific settings:

```toml
# Nova Unified Configuration File

# Graphlit API Configuration
[graphlit]
organization_id = "your-organization-id"
environment_id = "your-environment-id"
jwt_secret = "your-jwt-secret"

# Consolidate Markdown Configuration
[consolidate.global]
cm_dir = ".cm"
force_generation = false
no_image = false

# API Provider Configuration
api_provider = "openrouter"  # Options: "openai", "openrouter"

# OpenAI/OpenRouter Configuration
openai_key = "your-openai-key"
openrouter_key = "your-openrouter-key"

# Source Configurations
[[consolidate.sources]]
type = "bear"
srcDir = "/path/to/input/bear/notes"
destDir = "/path/to/output/bear/notes"

# Upload Configuration
[upload]
output_dir = "/path/to/output/directory"
```

### 2. Run Commands

Consolidate Markdown files:

```bash
nova consolidate-markdown
```

Upload to Graphlit (with dry run option):

```bash
nova upload-markdown --dry-run
```

Upload to Graphlit:

```bash
nova upload-markdown
```

Upload to Graphlit and delete existing content:

```bash
nova upload-markdown --delete-existing
```

## Documentation

For detailed usage instructions, see:

- [User Guide](docs/user_guide.md)
- [Quick Reference](docs/quick_reference.md)
- [Developer Documentation](docs/developer_guide.md)

## Development

### Prerequisites

- Python 3.8+
- UV (recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/username/nova.git
cd nova

# Create a virtual environment
uv venv create .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"

# Install pre-commit hooks
uv run pre-commit install
```

### Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=nova
```

### Linting

```bash
# Run linting
uv run ruff check .
uv run mypy src/

# Run formatting
uv run black src/ tests/
uv run isort src/ tests/

# Run all pre-commit checks
uv run pre-commit run --all-files
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Graphlit](https://github.com/username/graphlit) for the API client
- [ConsolidateMarkdown](https://github.com/username/consolidate-markdown) for the Markdown processing library
