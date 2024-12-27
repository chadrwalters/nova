# Nova Dependencies

## Core Dependencies

### System Requirements
- Python 3.9+
- ImageMagick 6.x
- Ghostscript
- Tesseract
- Git

### Python Packages
- **psutil**: System and process utilities
  - Version: 5.9.0+
  - Used for: Resource monitoring (CPU, memory, disk)
  - Required by: MonitoringManager

- **aiofiles**: Asynchronous file operations
  - Version: 23.1.0+
  - Used for: Async file I/O
  - Required by: BaseHandler, MonitoringManager

- **rich**: Console output formatting
  - Version: 13.3.0+
  - Used for: Console logging and progress display
  - Required by: BaseHandler, MonitoringManager

- **pyyaml**: YAML parsing
  - Version: 6.0.1+
  - Used for: Configuration files
  - Required by: Configuration system

- **click**: Command line interface
  - Version: 8.1.7+
  - Used for: CLI tools
  - Required by: Command line tools

### Optional Dependencies
- **pillow**: Image processing
  - Version: 9.5.0+
  - Used for: Image handling
  - Required by: ImageHandler

- **python-magic**: File type detection
  - Version: 0.4.27+
  - Used for: File type detection
  - Required by: BaseHandler

## Development Dependencies

### Testing
- **pytest**: Testing framework
  - Version: 7.4.0+
  - Used for: Unit and integration tests

- **pytest-asyncio**: Async test support
  - Version: 0.21.0+
  - Used for: Testing async functions

- **pytest-cov**: Coverage reporting
  - Version: 4.1.0+
  - Used for: Test coverage analysis

### Code Quality
- **black**: Code formatting
  - Version: 23.7.0+
  - Used for: Code style enforcement

- **isort**: Import sorting
  - Version: 5.12.0+
  - Used for: Import organization

- **flake8**: Linting
  - Version: 6.1.0+
  - Used for: Code quality checks

### Documentation
- **mkdocs**: Documentation generator
  - Version: 1.5.0+
  - Used for: Building documentation

- **mkdocs-material**: Documentation theme
  - Version: 9.1.0+
  - Used for: Documentation styling

## Installation

### Using Poetry
```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install with development dependencies
poetry install --with dev
```

### Using pip
```bash
# Install required packages
pip install -r requirements.txt

# Install development packages
pip install -r requirements-dev.txt
```

## Version Management
- All dependencies are managed through Poetry
- Version constraints are specified in pyproject.toml
- Lock file (poetry.lock) ensures reproducible builds
- Dependencies are regularly updated and tested

## Dependency Guidelines
1. Keep dependencies minimal and focused
2. Use stable, well-maintained packages
3. Regularly update dependencies
4. Test thoroughly after updates
5. Document breaking changes

## System Dependencies
Required system packages for Ubuntu/Debian:
```bash
apt-get update && apt-get install -y \
    python3.9 \
    python3.9-dev \
    imagemagick \
    ghostscript \
    tesseract-ocr \
    git \
    build-essential
```

Required system packages for macOS:
```bash
brew install \
    python@3.9 \
    imagemagick@6 \
    ghostscript \
    tesseract \
    git
```

## Environment Variables
```bash
# Required
NOVA_BASE_DIR=/path/to/base
NOVA_INPUT_DIR=/path/to/input
NOVA_OUTPUT_DIR=/path/to/output
NOVA_PROCESSING_DIR=/path/to/processing
NOVA_TEMP_DIR=/path/to/temp

# Optional
NOVA_LOG_LEVEL=INFO
NOVA_METRICS_ENABLED=true
NOVA_MONITORING_INTERVAL=60
``` 