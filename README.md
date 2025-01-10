# Nova

Nova is a Personal Knowledge Management System that integrates with Bear.app and uses Claude for intelligent querying.

## Features

- Bear.app export processing
- Document conversion with Docling
- Semantic chunking and embedding
- RAG pipeline with Claude integration
- Ephemeral data handling
- MCP SDK integration

## Installation

1. Clone the repository
2. Install dependencies:
```bash
poetry install
```

3. Set up pre-commit hooks:
```bash
poetry run pre-commit install
```

4. Create a `.env` file with your API keys:
```bash
ANTHROPIC_API_KEY=your_key_here
```

## Usage

Run Nova with the default configuration:
```bash
poetry run python -m nova.cli
```

Or specify a custom config file:
```bash
poetry run python -m nova.cli --config path/to/config.yaml
```

## Development

- Uses Poetry for dependency management
- Pre-commit hooks for code quality
- MyPy for type checking
- Black for code formatting
- isort for import sorting

## License

MIT 