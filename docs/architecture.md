# Nova Architecture

## Overview

Nova is a document processing system that transforms various document formats into structured markdown with metadata.

## Development Standards

### Code Quality Tools

The project enforces code quality through automated tools:

1. **Code Formatting**
   - Black for consistent Python formatting
   - Line length: 88 characters
   - Automatic formatting on commit

2. **Import Management**
   - isort with black profile
   - Consistent import grouping and ordering
   - Automatic sorting on commit

3. **Code Analysis**
   - flake8 for style guide enforcement
   - mypy for static type checking
   - bandit for security analysis

4. **Version Control**
   - Commitizen for standardized commit messages
   - Conventional commits format
   - Automated validation on commit

These tools are enforced through pre-commit hooks, ensuring consistent code quality across all contributions.

## Core Components

### Configuration Management

The configuration system uses a layered approach:

1. Default configuration (`src/nova/context_processor/config/default.yaml`)
2. User configuration (`config/nova.yaml`)

Configuration values are loaded in this order, with user config overriding defaults.

#### Configuration Files

The configuration files use YAML format and support:
- Path variables using `base_dir` reference
- User home directory expansion (`~`)
- Nested configuration sections
- Environment variable expansion (`${VAR}`)

Example configuration:
```yaml
base_dir: ~/nova
input_dir: ${base_dir}/input
output_dir: ${base_dir}/output
processing_dir: ${base_dir}/processing

apis:
  openai:
    api_key: ${OPENAI_API_KEY}
```

#### Configuration Loading

1. Load default configuration
2. Load user configuration
3. Merge configurations (user overrides default)
4. Expand environment variables and paths
5. Validate required fields
6. Create required directories

### Document Processing

The system processes documents through multiple phases, each with specific responsibilities and boundaries. For detailed information about each phase's implementation, features, and processing flow, see [Phases Documentation](phases.md).

### Metadata System

The metadata system provides comprehensive validation and tracking across processing phases:

#### Metadata Validation

The system includes a robust validation framework with multiple validation layers:

1. **Schema Validation**
   - Type-specific validation rules
   - Required field checks
   - Value range validation
   - Format consistency checks

2. **Cross-Phase Validation**
   - Version progression tracking
   - Immutable field consistency
   - Phase-specific requirements
   - State transition validation

3. **Related Metadata Validation**
   - Embedded file references
   - Archive content validation
   - Link integrity checks
   - Resource availability verification

#### Type-Specific Validation

Each file type has specialized validation rules:

1. **Image Metadata**
   - Dimension validation
   - DPI verification
   - Color mode consistency
   - Alpha channel validation

2. **Document Metadata**
   - Page count validation
   - Word count verification
   - Section structure checks
   - Content integrity validation

3. **Markdown Metadata**
   - Heading structure validation
   - Link integrity checks
   - Embedded file validation
   - Reference verification

4. **Archive Metadata**
   - File count validation
   - Size consistency checks
   - Content structure validation
   - Compression integrity

#### Version Control

The metadata system tracks versions across processing phases:

1. **Version Components**
   - Major version: Significant structural changes
   - Minor version: Content updates and refinements
   - Phase markers: Processing stage indicators

2. **Version Progression**
   - Monotonic version increases
   - Phase-appropriate version changes
   - Change tracking and history
   - Rollback prevention

### Document Handlers

The system includes specialized handlers for different document types, each implementing the BaseHandler interface. For detailed information about each handler's implementation, features, and processing flow, see [Handlers Documentation](handlers.md).

### Pipeline Management

The pipeline orchestrates document processing:
1. Identify document type
2. Select appropriate handler
3. Execute processing phases
4. Track progress and errors
5. Generate output files

#### File Processing Logic
- Files are processed based on their relationship to other documents:
  - Standalone files are processed independently
  - Referenced attachments (in dated directories) are tracked but not processed separately
  - Embedded documents are processed as part of their parent document
- File counts in pipeline statistics include:
  - Successfully processed standalone files
  - Referenced attachments (counted with their parent document)
  - Failed or skipped files

### Logging and Debugging

Comprehensive logging system with:
- Multiple log levels (ERROR, WARNING, INFO, DEBUG)
- Phase-specific logging
- Performance tracking
- Error reporting
- Rich console output with progress bars
- File logging with configurable paths
- Context-aware logging with phase and handler information

### Testing

The test suite is organized into several categories:
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Handler-specific tests for each document type
- Configuration tests
- Utility function tests

Test configuration is managed through `pytest.ini` with:
- Custom markers for test categorization
- Async test support with pytest-asyncio
- Detailed logging configuration
- Mock filesystem support

## Project Structure

The project is organized into the following main components:

### Core Modules
- `nova.context_processor.core`: Core functionality and base classes
- `nova.context_processor.config`: Configuration management
- `nova.context_processor.models`: Data models and schemas
- `nova.context_processor.handlers`: Document type handlers
- `nova.context_processor.phases`: Processing phase implementations
- `nova.context_processor.utils`: Utility functions and helpers
- `nova.context_processor.ui`: User interface components

### Command Line Interface
- `nova.context_processor.cli`: Main CLI entry point
- `nova.context_processor.cleanup`: Cleanup utilities

## Development Guidelines

See [Development Guidelines](development.md) for coding standards and practices.