# Nova Console Module

## Overview

The console module provides a comprehensive system for console output, logging, and progress tracking in the Nova document processing pipeline. It consists of three main components:

1. `ConsoleLogger`: Basic logging and formatting
2. `PhaseRunner`: Phase-level progress tracking
3. `PipelineReporter`: Pipeline-wide statistics and reporting

## Directory Structure

```
console/
├── __init__.py
├── color_scheme.py
├── console_logger.py
├── phase_runner.py
├── pipeline_reporter.py
└── README.md
```

## Quick Start

```python
from nova.core.console import ConsoleLogger, PhaseRunner, PipelineReporter

logger = ConsoleLogger()
runner = PhaseRunner()
reporter = PipelineReporter()

logger.info("Starting process...")
```

## Documentation

For detailed documentation, see:
- [Console Output System Guide](../../docs/console_output.md)
- [API Reference](../../docs/api/console.md)

## Testing

Run the console module tests:

```bash
pytest tests/core/test_console_logger.py
pytest tests/core/test_phase_runner.py
pytest tests/core/test_pipeline_reporter.py
```

## Contributing

When contributing to this module:

1. Follow the established color scheme in `color_scheme.py`
2. Add tests for new functionality
3. Update documentation for significant changes
4. Maintain backward compatibility
5. Consider performance implications 