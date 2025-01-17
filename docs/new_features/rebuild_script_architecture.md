# Nova Rebuild Script Technical Architecture

## Overview
This document outlines the technical architecture for implementing the improved rebuild script functionality, focusing on code organization, dependencies, and implementation details.

## System Components

### 1. Core Components

#### LoggingManager
```python
class LoggingManager:
    """Manages dynamic logging configuration and control."""
    def __init__(self):
        self.console = Console()
        self.current_level = "INFO"
        self.log_handlers = {}

    def set_log_level(self, level: str):
        """Dynamically updates logging level."""

    def setup_logging(self, initial_level: str = "INFO"):
        """Configures logging system with initial settings."""

    async def handle_log_command(self, command: str):
        """Handles runtime log level changes."""
```

#### RebuildManager
```python
class RebuildManager:
    """Manages the overall rebuild process and coordinates components."""
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.stats_collector = StatsCollector()
        self.health_checker = HealthChecker()
        self.logging_manager = LoggingManager()

    async def run_rebuild(self):
        """Main rebuild process orchestrator."""
```

#### ProgressManager
```python
class ProgressManager:
    """Handles progress tracking and UI updates."""
    def __init__(self):
        self.console = Console()
        self.progress = Progress()

    def create_progress_bar(self, description: str, total: int):
        """Creates a new progress bar."""
```

#### StatsCollector
```python
class StatsCollector:
    """Collects and aggregates system statistics."""
    def __init__(self):
        self.vector_stats = VectorStoreStats()
        self.system_stats = SystemStats()

    def collect_stats(self) -> Dict[str, Any]:
        """Collects all system statistics."""
```

#### HealthChecker
```python
class HealthChecker:
    """Performs system health checks."""
    def __init__(self):
        self.required_dirs = [...]
        self.required_files = [...]

    async def check_health(self) -> List[HealthStatus]:
        """Runs all health checks."""
```

### 2. File Structure

```
nova/
├── cli/
│   ├── commands/
│   │   ├── rebuild.py       # New rebuild command
│   │   └── monitor.py       # Existing monitor command
│   └── utils/
│       ├── progress.py      # Progress tracking utilities
│       ├── formatting.py    # Console formatting utilities
│       └── logging.py       # Logging utilities
├── rebuild/
│   ├── __init__.py
│   ├── manager.py          # RebuildManager implementation
│   ├── progress.py         # ProgressManager implementation
│   ├── stats.py           # StatsCollector implementation
│   ├── health.py          # HealthChecker implementation
│   └── logging.py         # LoggingManager implementation
└── scripts/
    └── rebuild.sh         # Main rebuild script
```

## Implementation Details

### 1. Progress Tracking
- Use Rich's Progress class for real-time updates
- Track multiple tasks simultaneously
- Show time estimates and completion percentages
- Handle nested progress indicators

```python
async def track_progress(self, task: RebuildTask):
    with Progress() as progress:
        task_id = progress.add_task(task.description, total=task.total)
        async for step in task.execute():
            progress.update(task_id, advance=1)
```

### 2. Statistics Collection
- Aggregate stats from multiple sources
- Track system resource usage
- Monitor vector store metrics
- Calculate processing times

```python
def collect_vector_stats(self) -> Dict[str, Any]:
    collection = self.vector_store.collection
    return {
        "total_docs": len(collection.get()["ids"]),
        "total_chunks": self.stats.total_chunks,
        "cache_hits": self.stats.cache_hits,
        # ... more stats
    }
```

### 3. Health Checking
- Verify system components
- Check file permissions
- Validate ChromaDB access
- Monitor resource availability

```python
async def verify_component(self, component: SystemComponent) -> HealthStatus:
    try:
        await component.check()
        return HealthStatus(status=True, message="Component healthy")
    except Exception as e:
        return HealthStatus(status=False, message=str(e))
```

### 4. Error Handling
- Graceful error recovery
- Detailed error messages
- Retry mechanisms
- User prompts for critical errors

```python
async def handle_error(self, error: RebuildError):
    if error.is_critical:
        await self.abort_rebuild()
    else:
        retry = await self.prompt_retry()
        if retry:
            await self.retry_operation()
```

### 1. Logging Control
- Dynamic log level management
- Context-aware logging filters
- Real-time log level switching
- Structured log formatting

```python
async def setup_logging(self):
    """Configure logging with dynamic control."""
    with Progress() as progress:
        # Configure base logging
        self.configure_base_logging()

        # Setup log handlers
        await self.setup_log_handlers()

        # Initialize runtime control
        await self.init_runtime_control()

async def handle_log_command(self, command: str):
    """Handle runtime log level changes."""
    if command in self.valid_levels:
        old_level = self.current_level
        self.current_level = command.upper()
        self.update_log_levels()
        self.console.print(f"[cyan]Changed log level: {old_level} -> {self.current_level}[/cyan]")
```

## Integration Points

### 1. CLI Integration
```python
@click.command()
@click.option("--log-level", type=click.Choice(['debug', 'info', 'warning', 'error']), default='info')
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option("--quiet", is_flag=True, help="Minimize output")
@click.option("--force", is_flag=True, help="Force rebuild without confirmation")
def rebuild(log_level: str, verbose: bool, quiet: bool, force: bool):
    """Improved rebuild command."""
    manager = RebuildManager()
    if verbose:
        log_level = 'debug'
    elif quiet:
        log_level = 'error'
    manager.logging_manager.setup_logging(log_level)
    manager.run_rebuild(force=force)
```

### 2. Monitoring Integration
```python
class MonitorCommand:
    """Enhanced monitor command with real-time updates."""
    def show_progress(self):
        """Show real-time progress information."""
```

### 3. Vector Store Integration
```python
class VectorStoreManager:
    """Enhanced vector store management."""
    async def rebuild_vectors(self):
        """Rebuild vector store with progress tracking."""
```

## Configuration

### 1. Progress Display Configuration
```python
PROGRESS_CONFIG = {
    "show_time": True,
    "show_percentage": True,
    "show_memory": True,
    "update_interval": 0.1
}
```

### 2. Health Check Configuration
```python
HEALTH_CHECK_CONFIG = {
    "required_dirs": [
        ".nova/vectors",
        ".nova/cache",
        ".nova/logs"
    ],
    "required_files": [
        ".nova/vectors/chroma.sqlite3"
    ]
}
```

### 1. Logging Configuration
```python
LOGGING_CONFIG = {
    "levels": {
        "debug": {"color": "blue", "show_path": True},
        "info": {"color": "green", "show_path": False},
        "warning": {"color": "yellow", "show_path": True},
        "error": {"color": "red", "show_path": True}
    },
    "format": {
        "debug": "{time} | {level} | {path}:{line} | {message}",
        "default": "{time} | {level} | {message}"
    },
    "handlers": {
        "console": {"level": "INFO", "format": "default"},
        "file": {"level": "DEBUG", "format": "debug"}
    }
}
```

## Testing Strategy

### 1. Unit Tests
```python
class TestRebuildManager:
    """Test rebuild manager functionality."""
    async def test_progress_tracking(self):
        """Test progress tracking accuracy."""
```

### 2. Integration Tests
```python
class TestRebuildIntegration:
    """Test full rebuild process."""
    async def test_complete_rebuild(self):
        """Test end-to-end rebuild process."""
```

### 1. Logging Tests
```python
class TestLoggingManager:
    """Test logging control functionality."""
    async def test_log_level_switching(self):
        """Test dynamic log level changes."""

    async def test_log_formatting(self):
        """Test log format by level."""
```

## Deployment Considerations

1. **Dependencies**
   - Rich library for terminal UI
   - Click for CLI
   - Psutil for system monitoring
   - ChromaDB for vector store

2. **Performance**
   - Async operations for I/O-bound tasks
   - Efficient progress updates
   - Minimal memory overhead

3. **Compatibility**
   - Support for different terminals
   - Cross-platform compatibility
   - Graceful fallback for unsupported features

## Future Enhancements

1. **Remote Monitoring**
   - WebSocket-based progress updates
   - Remote health checking
   - API endpoints for status

2. **Performance Optimization**
   - Cached statistics
   - Optimized progress updates
   - Resource usage optimization

3. **UI Improvements**
   - Custom progress visualizations
   - Interactive debugging
   - Theme support
