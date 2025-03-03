# Nova CLI Developer Guide

This guide provides information for developers who want to understand, modify, or extend the Nova CLI tool.

## Architecture Overview

Nova is built with a modular architecture that separates concerns and makes the codebase easy to maintain and extend. The main components are:

1. **CLI Entry Point**: Handles command-line arguments and dispatches to command handlers
2. **Command Handlers**: Implement the logic for each command
3. **Configuration Models**: Define and validate configuration using Pydantic with a unified approach
4. **Logging System**: Provides structured logging capabilities
5. **Exception Handling**: Defines custom exceptions for different error scenarios

### Directory Structure

```
nova/
├── __init__.py          # Package initialization
├── cli.py               # CLI entry point
├── commands/            # Command handlers
│   ├── __init__.py
│   ├── consolidate.py   # Consolidate-markdown command
│   └── upload.py        # Upload-markdown command
├── config/              # Configuration handling
│   ├── __init__.py
│   ├── loader.py        # Configuration loading utilities
│   └── models.py        # Pydantic models for unified configuration
├── utils/               # Utility functions
│   ├── __init__.py
│   └── logging.py       # Logging utilities
└── exceptions.py        # Custom exception classes
```

### Component Interactions

The following diagram illustrates how the components interact:

```
User Input → CLI Entry Point → Command Handler → Unified Configuration Model
                                      ↓
                                 External APIs
                                      ↓
                            Logging & Error Handling
```

## Core Components

### CLI Entry Point (`cli.py`)

The CLI entry point is responsible for:
- Parsing command-line arguments using `argparse`
- Setting up logging based on configuration
- Dispatching to the appropriate command handler
- Handling errors and providing appropriate exit codes

### Command Handlers (`commands/`)

Command handlers implement the logic for each command:
- `consolidate.py`: Implements the `consolidate-markdown` command
- `upload.py`: Implements the `upload-markdown` command

Each command handler follows a similar pattern:
1. Load and validate configuration
2. Set up logging
3. Execute the command logic
4. Handle errors and return appropriate status

### Configuration Models (`config/models.py`)

Configuration models use Pydantic to define and validate configuration:
- `GraphlitConfig`: For Graphlit API credentials
- `LoggingConfig`: For logging configuration
- `ConsolidateMarkdownConfig`: For the consolidate-markdown command
- `UploadMarkdownConfig`: For the upload-markdown command

### Logging System (`utils/logging.py`)

The logging system provides structured logging capabilities:
- `setup_logging`: Sets up logging based on configuration
- `get_logger`: Gets a logger with context
- `log_with_context`: Logs a message with context

### Exception Handling (`exceptions.py`)

Custom exceptions are defined for different error scenarios:
- `NovaError`: Base exception for all Nova-specific errors
- `ConfigurationError`: For configuration-related errors
- `ConsolidationError`: For errors during Markdown consolidation
- `UploadError`: For errors during Markdown upload
- `GraphlitClientError`: For errors related to the Graphlit client

## Development Workflow

### Setting Up the Development Environment

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

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=nova

# Run specific tests
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Code Quality Tools

Nova uses several tools to ensure code quality:

- **Ruff**: For linting and formatting
- **Black**: For code formatting
- **isort**: For import sorting
- **mypy**: For type checking
- **pre-commit**: For running checks before committing

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

## Extending Nova

### Adding a New Command

To add a new command to Nova:

1. Create a new file in the `commands` directory (e.g., `commands/new_command.py`)
2. Implement the command handler function
3. Add the command to the CLI entry point in `cli.py`
4. Create appropriate configuration models in `config/models.py`
5. Add tests for the new command

Example command handler:

```python
from pathlib import Path
from typing import Optional

from nova.config.loader import load_config
from nova.config.models import NewCommandConfig
from nova.exceptions import ConfigurationError, NewCommandError
from nova.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

def new_command(config_path: str) -> None:
    """
    Implement the new command.

    Args:
        config_path: Path to the configuration file

    Raises:
        ConfigurationError: If the configuration is invalid
        NewCommandError: If an error occurs during command execution
    """
    try:
        # Load and validate configuration
        config = load_config(config_path, NewCommandConfig)

        # Set up logging
        setup_logging(config.logging)

        # Command logic here
        logger.info("Executing new command")

        # ...

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error executing new command: {e}")
        raise NewCommandError(f"Failed to execute new command: {e}")
```

### Adding a New Configuration Model

To add a new configuration model:

1. Define the model in `config/models.py` using Pydantic
2. Add validators for fields as needed
3. Update the configuration loader in `config/loader.py` if necessary

Example configuration model:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class NewCommandConfig(BaseModel):
    """Configuration for the new command."""

    input_path: str = Field(..., description="Path to the input file")
    output_path: str = Field(..., description="Path to the output file")
    options: List[str] = Field(default_factory=list, description="Command options")

    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")

    @validator("input_path")
    def validate_input_path(cls, v):
        if not Path(v).exists():
            raise ValueError(f"Input path does not exist: {v}")
        return v
```

## Best Practices

### Error Handling

- Use custom exceptions for different error scenarios
- Catch exceptions at the appropriate level
- Log errors with context
- Provide clear error messages to users

### Logging

- Use structured logging
- Include context in log messages
- Use appropriate log levels
- Configure logging based on user preferences

### Testing

- Write unit tests for all components
- Write integration tests for end-to-end functionality
- Use mocks for external dependencies
- Aim for high test coverage

### Documentation

- Document all public functions and classes
- Keep the documentation up to date
- Provide examples for common use cases
- Document configuration options

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a new release on GitHub
4. Publish to PyPI

```bash
# Build the package
uv run python -m build

# Upload to PyPI
uv run python -m twine upload dist/*
```

## Troubleshooting

### Common Development Issues

#### Import Errors

If you encounter import errors during development, make sure:
- The package is installed in development mode (`uv pip install -e .`)
- The virtual environment is activated
- The import paths are correct

#### Test Failures

If tests are failing:
- Check the test output for specific errors
- Run the failing test with more verbosity (`uv run pytest -v tests/path/to/test.py`)
- Check if the test environment is properly set up

#### Pre-commit Hook Failures

If pre-commit hooks are failing:
- Run the specific check manually to see the error
- Fix the issues and try again
- Update the hooks if necessary (`uv run pre-commit autoupdate`)
