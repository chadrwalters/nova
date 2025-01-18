# Monitoring API Reference

## Classes

### MonitorCommand

Command-line interface for system monitoring.

```python
class MonitorCommand(NovaCommand):
    """Monitor Nova system."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        monitor: Optional[SessionMonitor] = None,
    ) -> None:
        """Initialize monitor command.

        Args:
            vector_store: Optional vector store instance
            monitor: Optional session monitor instance
        """
```

#### Methods

##### check_health
```python
def check_health(self) -> None:
    """Check system health."""
```
Displays health status of all system components.

##### show_stats
```python
def show_stats(self) -> None:
    """Show system statistics."""
```
Displays detailed system statistics including memory usage and performance metrics.

##### show_logs
```python
def show_logs(self) -> None:
    """Show system logs."""
```
Displays recent system logs with filtering capabilities.

##### show_profiles
```python
def show_profiles(self) -> None:
    """Show available profiles."""
```
Lists all available performance profiles.

##### start_profile
```python
def start_profile(self, name: str) -> None:
    """Start profiling.

    Args:
        name: Profile name
    """
```
Starts a new performance profile with the given name.

### SessionMonitor

Monitors system session and resources.

```python
class SessionMonitor:
    """Session monitoring for Nova system."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        log_manager: Optional[LogManager] = None,
    ) -> None:
        """Initialize session monitor.

        Args:
            vector_store: Optional vector store instance
            log_manager: Optional log manager instance
        """
```

#### Methods

##### check_health
```python
def check_health(self) -> Dict[str, Any]:
    """Check system health.

    Returns:
        Dictionary containing health status of all components
    """
```

##### get_stats
```python
def get_stats(self) -> Dict[str, Any]:
    """Get system statistics.

    Returns:
        Dictionary containing system statistics
    """
```

##### get_profiles
```python
def get_profiles(self) -> List[Dict[str, Any]]:
    """Get available performance profiles.

    Returns:
        List of profile information dictionaries
    """
```

##### start_profile
```python
@contextmanager
def start_profile(self, name: str) -> Generator[None, None, None]:
    """Start a performance profile.

    Args:
        name: Profile name

    Yields:
        None
    """
```

## Type Definitions

### MemoryStatus
```python
class MemoryStatus(TypedDict):
    """Memory status information."""
    status: str  # "healthy" | "warning" | "critical"
```

### HealthStatus
```python
class HealthStatus(TypedDict):
    """System health status information."""
    memory: MemoryStatus
    vector_store: str
    monitor: str
    logs: str
    session_uptime: float
    status: str
```

### ProcessStats
```python
class ProcessStats(TypedDict):
    """Process statistics."""
    current_memory_mb: float
    peak_memory_mb: float
    warning_count: int
```

### SystemStats
```python
class SystemStats(TypedDict):
    """System statistics."""
    memory: MemoryStats
    session: SessionStats
    profiles: List[Dict[str, Any]]
```

## Usage Examples

### Health Check
```python
from nova.cli.commands.monitor import MonitorCommand

# Create command instance
cmd = MonitorCommand()

# Check system health
cmd.check_health()
```

### Performance Profiling
```python
# Start a profile
with cmd.monitor.start_profile("my_profile"):
    # Code to profile
    perform_operation()

# View profiles
cmd.show_profiles()
```

### System Statistics
```python
# Get raw statistics
stats = cmd.monitor.get_stats()

# Display formatted statistics
cmd.show_stats()
```

### Log Viewing
```python
# View recent logs
cmd.show_logs()
```

## Error Handling

The monitoring system uses Python's exception handling:

```python
try:
    cmd.check_health()
except Exception as e:
    logger.error(f"Health check failed: {e}")
```

Common exceptions:
- `ComponentUnavailableError`: Component not accessible
- `ResourceExhaustedError`: Resource limits exceeded
- `InvalidProfileError`: Invalid profile operation

## Testing

The monitoring system includes comprehensive tests:

```python
def test_check_health(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test health check functionality."""
    mock_monitor.check_health.return_value = {
        "memory": {"status": "healthy"},
        "vector_store": "healthy",
        "monitor": "healthy",
        "logs": "healthy",
        "session_uptime": 123.45,
        "status": "healthy"
    }
    command.check_health()
    assert mock_monitor.check_health.call_count == 1
```
