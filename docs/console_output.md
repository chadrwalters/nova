# Nova Console Output System

The Nova Console Output System provides a robust and flexible way to display progress, logs, and statistics during document processing. This guide explains how to use the system effectively.

## Components

### 1. ConsoleLogger

The `ConsoleLogger` class handles basic logging and formatting:

```python
from nova.core.console import ConsoleLogger

logger = ConsoleLogger()

# Basic logging
logger.info("Processing file...")
logger.warning("Missing metadata")
logger.error("Failed to process image")
logger.success("Completed successfully")

# Progress tracking
with logger.progress("Processing files") as progress:
    progress.update(50)  # Update to 50%
    
# Table output
logger.table(
    headers=["File", "Status", "Time"],
    rows=[["doc1.md", "Success", "2.3s"]]
)

# Batch logging
with logger.batch() as batch:
    batch.info("Step 1")
    batch.info("Step 2")
```

### 2. PhaseRunner

The `PhaseRunner` manages individual processing phases:

```python
from nova.core.console import PhaseRunner

runner = PhaseRunner()

# Start a phase
runner.start_phase("MARKDOWN_PARSE")

# Update progress
runner.update_progress(files_processed=10, total_files=20)

# End phase and get stats
stats = runner.end_phase()
print(f"Files processed: {stats.processed_count}")
```

### 3. PipelineReporter

The `PipelineReporter` tracks overall pipeline progress:

```python
from nova.core.console import PipelineReporter

reporter = PipelineReporter()

# Start pipeline
reporter.start_pipeline()

# Add phase statistics
reporter.add_phase_stats("MARKDOWN_PARSE", phase_stats)
reporter.add_phase_stats("MARKDOWN_CONSOLIDATE", phase_stats)

# End pipeline and get summary
summary = reporter.end_pipeline()
print(f"Total processing time: {summary.total_time}")
```

## Color Scheme

The system uses a consistent color scheme for different types of output:

- Title: Bold Blue
- Path: Cyan
- Stats: Bold Cyan
- Success: Green
- Warning: Yellow
- Error: Red
- Info: Blue
- Highlight: Magenta
- Detail: Dim White
- Cache: Cyan
- Progress: Green
- Skip: Yellow

## Best Practices

1. **Use Context Managers**: Prefer using context managers (`with` statements) for progress tracking and batch logging.

2. **Consistent Logging Levels**: Use appropriate logging levels:
   - `info`: General progress information
   - `warning`: Non-critical issues
   - `error`: Critical problems
   - `success`: Completed operations

3. **Progress Updates**: Keep progress updates reasonable (not too frequent) to avoid console spam.

4. **Phase Management**: Always properly start and end phases using PhaseRunner.

5. **Pipeline Statistics**: Collect and report statistics for all phases to provide comprehensive pipeline reports.

## Configuration

The console output system can be configured through environment variables:

```bash
NOVA_LOG_LEVEL=INFO          # Logging level (DEBUG, INFO, WARNING, ERROR)
NOVA_CONSOLE_COLOR=1         # Enable/disable colored output (0/1)
NOVA_PROGRESS_REFRESH=0.5    # Progress bar refresh rate in seconds
```

## Example Usage

Here's a complete example showing how to use all components together:

```python
from nova.core.console import ConsoleLogger, PhaseRunner, PipelineReporter

# Initialize components
logger = ConsoleLogger()
runner = PhaseRunner()
reporter = PipelineReporter()

# Start pipeline
reporter.start_pipeline()

# Process markdown files
with logger.progress("Processing markdown files") as progress:
    runner.start_phase("MARKDOWN_PARSE")
    
    for i, file in enumerate(files):
        logger.info(f"Processing {file}")
        # Process file...
        runner.update_progress(files_processed=i+1, total_files=len(files))
        progress.update((i+1)/len(files) * 100)
    
    phase_stats = runner.end_phase()
    reporter.add_phase_stats("MARKDOWN_PARSE", phase_stats)

# End pipeline and show summary
summary = reporter.end_pipeline()
logger.table(
    headers=["Phase", "Files", "Time"],
    rows=[[name, stats.processed_count, stats.elapsed_time] 
          for name, stats in summary.phase_stats.items()]
)
```

## Error Handling

The system includes comprehensive error handling:

```python
try:
    with logger.progress("Risky operation") as progress:
        # ... operation that might fail
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
    # Handle error appropriately
```

## Performance Considerations

1. Batch logging when processing many items
2. Use appropriate progress update frequency
3. Clean up resources by properly ending phases
4. Monitor memory usage with large pipelines

## Troubleshooting

Common issues and solutions:

1. **Missing Colors**: Ensure NOVA_CONSOLE_COLOR=1 and terminal supports colors
2. **Progress Bar Issues**: Check NOVA_PROGRESS_REFRESH rate
3. **Memory Usage**: Use batch logging for large operations
4. **Incomplete Statistics**: Verify all phases are properly ended 