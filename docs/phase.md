# Nova Phase Interface

## Overview
The Nova phase interface provides a unified base for implementing pipeline phases. Each phase represents a discrete step in the document processing pipeline, with standardized initialization, processing, validation, and cleanup procedures.

## Core Components

### Phase Base Class
The `Phase` class is the abstract base class for all pipeline phases. It provides:
- Standardized lifecycle management
- Resource monitoring integration
- Error handling and recovery
- Context management
- State tracking
- Processor initialization
- Hook system for extensibility

### Phase State
Each phase maintains its state through two mechanisms:
1. `PhaseState` object for tracking:
   - Processed files
   - Failed files
   - Skipped files
   - Errors and warnings
   - Metrics
   - Timing information

2. Status string for lifecycle tracking:
   - "initialized": Phase is ready for processing
   - "completed": Phase has completed successfully
   - "error": Phase encountered an error
   - "cleaned": Phase resources have been cleaned up

## Usage

### Basic Phase Implementation
```python
from pathlib import Path
from typing import Dict, Any, Optional
from nova.core.pipeline.phase import Phase
from nova.core.models.result import ProcessingResult
from nova.core.config import ProcessorConfig

class CustomPhase(Phase):
    def __init__(self, name: str, config: ProcessorConfig, monitor=None):
        """Initialize the phase."""
        self._status = "initialized"
        super().__init__(name, config, monitor)
    
    async def process(self, input_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process the input path."""
        try:
            # Process the input
            result = await self._process_impl(input_path, context)
            self._status = "completed"
            return result
        except Exception as e:
            self._status = "error"
            raise
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing result."""
        return result.success and not result.errors
    
    async def initialize(self) -> None:
        """Initialize phase resources."""
        self._status = "initialized"
    
    async def cleanup(self) -> None:
        """Clean up phase resources."""
        self._status = "cleaned"
```

### Context Handling
```python
async def process_with_context(phase: Phase, input_path: Path):
    # Create processing context
    context = {
        "options": {"preserve_metadata": True},
        "dependencies": ["file1.txt", "file2.txt"]
    }
    
    # Process with context
    result = await phase.process(input_path, context)
    
    # Context is preserved in phase
    assert phase.context == context
```

### Error Handling
```python
class ErrorPhase(Phase):
    async def process(self, input_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        try:
            # Attempt processing
            result = await self._process_impl(input_path, context)
            
            # Validate result
            if not self.validate(result):
                self._status = "error"
                return result
            
            self._status = "completed"
            return result
            
        except Exception as e:
            # Handle error
            self._status = "error"
            self.state.add_error(str(e))
            raise
```

### Monitoring Integration
```python
class MonitoredPhase(Phase):
    async def process(self, input_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        async with self.monitor.async_monitor_operation(f"{self.name}_process"):
            # Monitor resource usage
            usage = self.monitor.capture_resource_usage()
            self.state.add_metric("cpu_percent", usage.cpu_percent)
            
            # Process with monitoring
            result = await super().process(input_path, context)
            
            # Record metrics
            self.monitor.increment_counter("files_processed")
            return result
```

## Configuration
Phases are configured through the `ProcessorConfig` class:

```python
config = ProcessorConfig(
    name="custom_phase",
    description="Custom processing phase",
    processor="package.module.CustomProcessor",
    output_dir="/path/to/output",
    options={
        "preserve_metadata": True,
        "handle_errors": True
    }
)

phase = CustomPhase(name="custom_phase", config=config)
```

## Testing
The phase interface includes comprehensive tests in `tests/core/pipeline/test_phase_interface.py`:

### Lifecycle Tests
- `test_phase_initialization`: Phase initialization
- `test_phase_lifecycle`: Complete phase lifecycle
- `test_phase_error_handling`: Error handling and recovery

### Validation Tests
- `test_phase_validation`: Result validation
- `test_phase_context_handling`: Context management

Run the tests with:
```bash
# Run phase interface tests
pytest tests/core/pipeline/test_phase_interface.py

# Run with coverage
pytest --cov=nova.core.pipeline.phase tests/core/pipeline/test_phase_interface.py
```

## Best Practices

### Phase Implementation
1. Always call super().__init__() in phase constructors
2. Implement all abstract methods
3. Handle cleanup properly
4. Validate processing results
5. Use appropriate status values

### State Management
1. Use PhaseState for tracking metrics and files
2. Use status for lifecycle tracking
3. Update state consistently
4. Clean up state in cleanup()
5. Handle state in error cases

### Error Handling
1. Set appropriate status on errors
2. Clean up resources on errors
3. Record errors in state
4. Provide meaningful error messages
5. Implement recovery where possible

### Testing
1. Test all lifecycle methods
2. Verify state transitions
3. Test error conditions
4. Validate context handling
5. Test with monitoring 