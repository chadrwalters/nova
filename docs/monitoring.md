# Nova Monitoring System

## Overview
The Nova monitoring system provides comprehensive monitoring and metrics tracking for the document processing pipeline. It integrates with the metrics system to track resource usage, operation timing, and processing status across all phases and handlers.

## Core Components

### MonitoringManager
The `MonitoringManager` class is the central component of the monitoring system. It provides:
- Resource usage monitoring (CPU, memory, disk)
- Operation timing and tracking
- Error and warning recording
- Metrics integration
- Threshold monitoring
- Async operation support
- Nested operation tracking
- Context preservation

### ResourceUsage
The `ResourceUsage` data class captures system resource metrics:
- CPU usage percentage
- Memory usage percentage
- Memory used (bytes)
- Disk used (bytes)
- Disk free (bytes)
- Timestamp of capture

## Usage

### Basic Monitoring
```python
from nova.core.utils.monitoring import MonitoringManager

# Create a monitoring manager
monitoring = MonitoringManager()

# Monitor an operation
with monitoring.monitor_operation("operation_name"):
    # Perform operation
    process_file()

# Check metrics
metrics = monitoring.metrics
operations = metrics.get("operations_completed", 0)
errors = metrics.get("errors", 0)
```

### Async Monitoring
```python
async with monitoring.async_monitor_operation("async_operation"):
    # Perform async operation
    await process_file_async()
    
    # Nested operations are supported
    async with monitoring.async_monitor_operation("nested_operation"):
        await process_part_async()
```

### Resource Monitoring
```python
# Get current resource usage
usage = monitoring.capture_resource_usage()
print(f"CPU: {usage.cpu_percent}%")
print(f"Memory: {usage.memory_percent}%")
print(f"Memory Used: {usage.memory_used} bytes")
print(f"Disk Used: {usage.disk_used} bytes")
print(f"Disk Free: {usage.disk_free} bytes")
```

### Error Recording
```python
try:
    process_file()
except Exception as e:
    monitoring.record_error(f"Error processing file: {str(e)}")
    # Error count is automatically tracked
    assert monitoring.metrics["errors"] > 0
```

### Metrics Integration
```python
# Increment counters
monitoring.increment_counter("files_processed")

# Get all metrics
metrics = monitoring.metrics

# Check operation timings
timings = metrics["timings"]
for operation, durations in timings.items():
    avg_duration = sum(durations) / len(durations)
    print(f"{operation}: {avg_duration:.3f}s average")
```

## Handler Integration
All handlers should use the monitoring system through the base handler:

```python
class CustomHandler(BaseHandler):
    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        try:
            async with self.monitoring.async_monitor_operation("read_file"):
                # Read file
                content = await self.read_file(file_path)
                
                # Track resource usage
                usage = self.monitoring.capture_resource_usage()
                self.monitoring.set_threshold("memory_percent", 85.0)
                self.monitoring._check_thresholds(usage)
            
            async with self.monitoring.async_monitor_operation("process_content"):
                # Process content
                result = await self.process_content(content)
                
                # Record success
                self.monitoring.increment_counter("files_processed")
                
            return result
            
        except Exception as e:
            # Record error
            self.monitoring.record_error(f"Error processing {file_path}: {str(e)}")
            return ProcessingResult(success=False, errors=[str(e)])
```

## Configuration
The monitoring system can be configured through the handler configuration:

```python
config = {
    'monitoring': {
        'thresholds': {
            'cpu_percent': 90.0,
            'memory_percent': 85.0,
            'disk_percent': 80.0
        },
        'metrics': {
            'enabled': True,
            'save_interval': 300  # seconds
        }
    }
}
```

## Metrics Output
The monitoring system provides comprehensive metrics tracking:
- Operation timing statistics
- Resource usage trends
- Error and warning counts
- Custom counters
- Processing status
- Threshold violations

Example metrics output:
```json
{
    "timings": {
        "read_file": [0.125, 0.130, 0.128],
        "process_content": [0.250, 0.245, 0.255]
    },
    "counters": {
        "files_processed": 10,
        "errors": 0,
        "warnings": 0
    },
    "resource_usage": {
        "cpu_percent": 25.5,
        "memory_percent": 45.2,
        "memory_used": 1024000,
        "disk_used": 5000000,
        "disk_free": 10000000
    }
}
```

## Best Practices

### Operation Monitoring
1. Use descriptive operation names
2. Monitor discrete operations separately
3. Take advantage of nested operation tracking
4. Handle errors appropriately
5. Clean up resources in finally blocks

### Resource Monitoring
1. Set appropriate thresholds
2. Monitor long-running operations
3. Track resource trends
4. Handle threshold alerts
5. Clean up resources promptly

### Error Handling
1. Record detailed error messages
2. Include context information
3. Track error patterns
4. Implement recovery mechanisms
5. Clean up after errors

### Metrics
1. Use meaningful metric names
2. Record relevant measurements
3. Track success and failure
4. Monitor performance trends
5. Save metrics regularly

## Testing
The monitoring system includes comprehensive tests in `tests/core/utils/test_monitoring.py`:

### Operation Tests
- `test_monitor_operation`: Basic operation monitoring
- `test_monitor_multiple_operations`: Multiple operation tracking
- `test_monitor_nested_operations`: Nested operation support
- `test_monitor_operation_timing`: Operation timing accuracy

### Resource Tests
- `test_resource_monitoring`: Resource usage tracking
- `test_resource_usage`: ResourceUsage data class
- `test_monitor_thresholds`: Threshold monitoring

### Error Handling Tests
- `test_record_error`: Error recording
- `test_monitor_operation_with_error`: Error handling in operations

### Metrics Tests
- `test_increment_counter`: Counter functionality
- `test_get_metrics`: Metrics retrieval

Run the tests with:
```bash
# Run monitoring tests
pytest tests/core/utils/test_monitoring.py

# Run with coverage
pytest --cov=nova.core.utils.monitoring tests/core/utils/test_monitoring.py
``` 