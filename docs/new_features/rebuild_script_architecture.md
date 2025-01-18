# Nova Rebuild Script Technical Architecture

## Overview
This document outlines the technical architecture for enhancing the rebuild script functionality by extending existing Nova components and adding new capabilities where needed.

## System Components

### 1. Extended Core Components

#### Enhanced MonitorCommand
```python
class MonitorCommand:
    """Extended monitor command with rebuild-specific features."""
    def _check_health(self):
        """Enhanced health checks including rebuild status."""
        # Existing health checks
        super()._check_health()

        # Additional rebuild-specific checks
        self._check_rebuild_status()
        self._verify_rebuild_components()

    def _show_stats(self):
        """Enhanced stats including rebuild metrics."""
        # Existing stats
        super()._show_stats()

        # Additional rebuild metrics
        self._show_rebuild_stats()
```

#### Enhanced SessionMonitor
```python
class SessionMonitor:
    """Enhanced session monitor with rebuild tracking."""
    def track_rebuild_progress(self):
        """Track rebuild-specific metrics."""
        self.metrics.rebuild_start = datetime.now()
        self.metrics.chunks_processed = 0
        self.metrics.processing_time = 0.0

    def update_rebuild_progress(self, chunks: int, time: float):
        """Update rebuild progress metrics."""
        self.metrics.chunks_processed = chunks
        self.metrics.processing_time = time
```

#### Enhanced NovaCommand
```python
class NovaCommand:
    """Enhanced base command with improved progress and error handling."""
    def create_progress(self):
        """Create enhanced progress display."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            MofNCompleteColumn()
        )

    def handle_error(self, error: Exception):
        """Enhanced error handling with recovery options."""
        if isinstance(error, RebuildError):
            return self._handle_rebuild_error(error)
        return super().handle_error(error)
```

### 2. File Structure

```
nova/
├── cli/
│   ├── commands/
│   │   ├── rebuild.py       # Enhanced rebuild command
│   │   └── monitor.py       # Extended monitor command
│   └── utils/
│       ├── progress.py      # Enhanced progress utilities
│       └── formatting.py    # Console formatting utilities
└── monitoring/
    ├── session.py          # Enhanced session monitoring
    └── persistent.py       # Enhanced persistent monitoring
```

## Implementation Details

### 1. Enhanced Progress Tracking
- Extend existing Rich progress bars
- Add time remaining estimates
- Show resource usage
- Track multiple tasks

```python
def track_progress(self, task: RebuildTask):
    """Enhanced progress tracking."""
    with self.create_progress() as progress:
        task_id = progress.add_task(
            task.description,
            total=task.total,
            show_time=True,
            show_memory=True
        )
        async for step in task.execute():
            progress.update(task_id, advance=1)
            self.session_monitor.update_rebuild_progress(
                step.chunks_processed,
                step.processing_time
            )
```

### 2. Enhanced Statistics Collection
- Extend existing vector store stats
- Add rebuild-specific metrics
- Track system resources
- Calculate performance trends

```python
def collect_rebuild_stats(self) -> Dict[str, Any]:
    """Collect enhanced rebuild statistics."""
    # Get existing vector store stats
    stats = super().collect_vector_stats()

    # Add rebuild-specific stats
    stats.update({
        "rebuild_duration": self.session_monitor.metrics.processing_time,
        "chunks_per_second": self.calculate_processing_rate(),
        "peak_memory_usage": self.get_peak_memory(),
        "success_rate": self.calculate_success_rate()
    })

    return stats
```

### 3. Enhanced Health Checking
- Extend existing health checks
- Add rebuild-specific validation
- Monitor resource usage
- Track component status

```python
async def verify_rebuild_status(self) -> HealthStatus:
    """Enhanced rebuild health verification."""
    try:
        # Check existing components
        base_status = await super().verify_component()

        # Additional rebuild checks
        rebuild_checks = await self._verify_rebuild_components()

        return HealthStatus(
            status=base_status.status and all(rebuild_checks),
            message=self._format_health_message(base_status, rebuild_checks)
        )
    except Exception as e:
        return HealthStatus(status=False, message=str(e))
```

### 4. Enhanced Error Handling
- Extend existing error handling
- Add rebuild-specific recovery
- Provide detailed context
- Support retry operations

```python
async def handle_rebuild_error(self, error: RebuildError):
    """Enhanced rebuild error handling."""
    # Log error with context
    self.log_error(f"Rebuild error: {error}", context=error.context)

    # Check if recoverable
    if error.is_recoverable:
        return await self._attempt_recovery(error)

    # Handle critical errors
    await self._handle_critical_error(error)
```

## Integration Points

### 1. CLI Integration
```python
@click.command()
@click.option("--log-level", type=click.Choice(['debug', 'info', 'warning', 'error']))
@click.option("--force", is_flag=True, help="Force rebuild without confirmation")
def rebuild(log_level: str, force: bool):
    """Enhanced rebuild command."""
    manager = RebuildManager()
    manager.run_rebuild(
        force=force,
        log_level=log_level,
        progress_callback=manager.session_monitor.update_rebuild_progress
    )
```

### 2. Monitoring Integration
```python
class MonitorCommand:
    """Enhanced monitor command."""
    def show_rebuild_progress(self):
        """Show real-time rebuild progress."""
        stats = self.session_monitor.get_rebuild_stats()
        self.console.print(self._format_rebuild_stats(stats))
```

## Configuration

### 1. Progress Display Configuration
```python
PROGRESS_CONFIG = {
    "show_time": True,
    "show_percentage": True,
    "show_memory": True,
    "update_interval": 0.1,
    "show_spinner": True
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
    ],
    "resource_thresholds": {
        "memory_percent": 80,
        "disk_percent": 90,
        "cpu_percent": 75
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
