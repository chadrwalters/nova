# Nova Core Module

This directory contains the core functionality of the Nova document processor. The code is organized as follows:

## Directory Structure

```
core/
├── config/                 # Configuration management
│   ├── __init__.py
│   ├── base.py            # Base configuration classes
│   ├── paths.py           # Path configuration
│   └── processor.py       # Processor configuration
├── pipeline/              # Pipeline management
│   ├── __init__.py
│   ├── base.py           # Base pipeline classes
│   ├── manager.py        # Pipeline orchestration
│   └── phase.py          # Phase definitions
├── processors/           # Base processor implementations
│   ├── __init__.py
│   ├── base.py          # Base processor class
│   └── mixins/          # Reusable processor functionality
├── utils/               # Core utilities
│   ├── __init__.py
│   ├── logging.py      # Logging configuration
│   ├── retry.py        # Retry logic
│   └── validation.py   # Validation utilities
├── models/             # Core data models
│   ├── __init__.py
│   ├── document.py     # Document model
│   └── state.py       # State management
├── errors.py          # Error definitions
└── __init__.py        # Core module initialization

## Key Components

1. Configuration (`config/`)
   - Centralized configuration management
   - Path handling and validation
   - Processor-specific configuration

2. Pipeline (`pipeline/`)
   - Pipeline orchestration and management
   - Phase definitions and transitions
   - Error handling and recovery

3. Processors (`processors/`)
   - Base processor implementations
   - Common processor functionality
   - Reusable mixins

4. Utilities (`utils/`)
   - Logging configuration
   - Retry mechanisms
   - Validation utilities

5. Models (`models/`)
   - Core data structures
   - State management
   - Document representation

## Usage

The core module provides the foundation for the Nova document processor. Each component is designed to be:

- Modular: Components can be used independently
- Extensible: Easy to add new functionality
- Reusable: Common patterns are abstracted into mixins
- Type-safe: Full type hints and validation

## Best Practices

1. Keep the core module focused on essential functionality
2. Use abstract base classes for interfaces
3. Implement common functionality in mixins
4. Maintain clear separation of concerns
5. Document all public interfaces
6. Include type hints and validation
7. Follow consistent error handling patterns

## Example

```python
from nova.core.pipeline import PipelineManager
from nova.core.config import ProcessorConfig

# Create pipeline manager
manager = PipelineManager()

# Configure and run pipeline
config = ProcessorConfig(
    enabled=True,
    output_dir="output"
)

result = manager.run_pipeline(config)
```

## Development

When adding new functionality to the core module:

1. Consider if it belongs in core or should be phase-specific
2. Use existing abstractions and patterns
3. Add appropriate tests and documentation
4. Update this README if adding new components 