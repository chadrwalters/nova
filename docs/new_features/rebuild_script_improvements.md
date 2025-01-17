# Nova Rebuild Script Improvements PRD

## Overview
This document outlines improvements to the Nova rebuild script to provide a more user-friendly, informative, and reliable experience during system rebuilds.

## Goals
1. Enhance user feedback during long-running operations
2. Provide clear, structured progress indicators
3. Improve error handling and reporting
4. Present comprehensive system statistics
5. Maintain consistent styling and formatting
6. Provide intuitive logging level control

## Current Pain Points
1. Limited real-time feedback during long operations
2. Inconsistent error handling across steps
3. Basic console output without visual hierarchy
4. Statistics spread across multiple commands
5. No clear indication of overall progress
6. Difficult to adjust logging verbosity for debugging

## Proposed Features

### 1. Dynamic Logging Control
- Simple command-line flags for log levels (--verbose, --quiet, --debug)
- Real-time log level adjustment during execution
- User-friendly log formatting based on level
- Context-aware log filtering
- Easy-to-understand log categories

### 2. Structured Console Output
- Clear visual hierarchy with sections and subsections
- Consistent styling using Rich library
- Emoji or ASCII banners for major steps
- Color-coded status indicators

### 3. Real-time Progress Tracking
- Progress bars for long-running operations
- Time estimates for each major step
- Chunk processing statistics in real-time
- Memory usage monitoring

### 4. Enhanced Error Handling
- Graceful error recovery
- Clear error messages with context
- Suggestions for resolving common issues
- Option to continue or abort on non-critical errors

### 5. Comprehensive Statistics
- Vector store metrics
- Processing statistics
- System health indicators
- Performance metrics
- Cache statistics

### 6. Final Summary Report
- Overall execution time
- Total items processed
- Success/failure status
- System health status
- Resource usage summary

## Technical Requirements

### Logging Control Interface
```
# Command-line usage
uv run python -m nova.cli rebuild --log-level=debug
uv run python -m nova.cli rebuild --verbose
uv run python -m nova.cli rebuild --quiet

# Runtime control
[cyan]Current log level: INFO[/cyan]
Type 'debug', 'info', 'warning', or 'error' to change logging detail
> debug
[cyan]Switched to DEBUG logging[/cyan]
```

### Console Output Format
```
[bold cyan]Nova Rebuild Process (v0.1.0) - 2025-01-17 06:15:26[/bold cyan]
-------------------------------------------------

[yellow bold]Cleanup Phase[/yellow bold]
  • 🗑️  Removing Nova system directories... [Done]
  • 🗑️  Removing old logs... [Done]
  • 🧹 Cleaning vector store... [Done]

[green]✔[/green] All cleanup steps completed successfully.

[blue bold]Step 1: Processing Notes[/blue bold]
Processing notes (20/20) [100%] – 30 seconds
[green]✔[/green] Notes discovered: 20
[green]✔[/green] Output directory: .nova/processing

[blue bold]Step 2: Building Vector Embeddings[/blue bold]
Chunks processed: 643 in total [100%] – 1 min 48s
[green]✔[/green] Stored 643 chunks in vector store
[green]✔[/green] Approx. memory usage peak: 700 MB

[green bold]System Health Check[/green bold]
  [green]✅[/green] Vector store directory exists
  [green]✅[/green] ChromaDB database exists
  [green]✅[/green] Cache directory exists
  [green]✅[/green] Logs directory exists
  [green]✅[/green] ChromaDB collection is accessible

[bold]System Statistics[/bold]
  Vector Store Statistics
    • Documents in collection: 643
    • Total chunks: 643
    • Total embeddings: 0
    • Cache hits: 0
    • Cache misses: 0

[green bold]✅ Rebuild complete![/green bold] Total time: 2m 32s
```

### Required Dependencies
- Rich library for terminal formatting
- Click for CLI interface
- Psutil for system resource monitoring
- Loguru for advanced logging control

## Success Metrics
1. Reduced user confusion during rebuilds
2. Faster problem identification
3. More accurate progress estimates
4. Improved error resolution time
5. Better system health visibility
6. Reduced time spent on log analysis

## Future Considerations
1. Interactive mode for debugging
2. Remote monitoring capability
3. Performance optimization tracking
4. Custom progress visualization plugins
5. Integration with monitoring dashboards
