# Nova Development Quick Start Guide

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/nova.git
   cd nova
   ```

2. Install Poetry:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```bash
   poetry install
   ```

4. Set up development environment:
   ```bash
   poetry run python -m nova.dev
   ```

## Development Mode

Nova includes a development mode that provides:
- Debug logging
- Hot reload
- Mock services
- Performance tracking
- Development tools

### Configuration

Development settings are in `config/nova.dev.yaml`. Key settings:

```yaml
dev_mode:
  enabled: true
  debug_logging: true
  hot_reload: true
  mock_services: true
```

### Using Development Tools

1. Initialize dev mode:
   ```python
   from nova.dev import initialize_dev_mode
   
   dev_mode = initialize_dev_mode()
   ```

2. Profile code:
   ```python
   from nova.dev import DevTools
   
   tools = DevTools(dev_mode)
   
   with tools.profile("my_function"):
       # Code to profile
       process_data()
   ```

3. Mock data:
   ```python
   from nova.dev import MockData
   
   mock_data = MockData(dev_mode)
   test_data = mock_data.load_scenario("basic_load")
   ```

4. Mock responses:
   ```python
   @tools.mock_response({"status": "success"})
   def api_call():
       # Real implementation
       pass
   ```

## Development Server

Run the development server:
```bash
poetry run python -m nova --config config/nova.dev.yaml
```

Features:
- Auto-reload on code changes
- CORS enabled for frontend development
- Debug endpoints enabled
- Performance profiling
- Metrics UI at http://localhost:8001

## Mock Data

Mock data scenarios are in `tests/fixtures/`:
- `basic_load.yaml`: Basic test data
- `high_memory.yaml`: High memory usage scenario
- `search_latency.yaml`: Search performance testing
- `error_conditions.yaml`: Error handling scenarios

Example scenario:
```yaml
vectors:
  count: 1000
  dimension: 384

queries:
  - text: "Test query"
    expected_results: 5
    latency_ms: 100
```

## Development Tools

### Profiler

Profile code performance:
```python
with tools.profile("search_function"):
    results = vector_store.search(query_vector)
```

Profiles are saved to `.nova/profiles/` and include:
- Function call counts
- Time per function
- Memory allocation
- Call graphs

### Debugger

Remote debugging is enabled on port 5678:
```python
import debugpy

debugpy.listen(5678)
debugpy.wait_for_client()  # Optional: wait for debugger
```

### Metrics UI

Monitor performance metrics:
1. Start the metrics UI: `poetry run python -m nova.dev.metrics_ui`
2. Open http://localhost:8001
3. View:
   - Vector store performance
   - Memory usage
   - Search latency
   - System health

## Testing

Run tests with development settings:
```bash
poetry run pytest --dev-mode
```

Features:
- Mock responses enabled
- Rate limits disabled
- Fast cleanup
- GPU tests skipped

## Common Tasks

### Adding Mock Data

1. Create scenario file in `tests/fixtures/`
2. Add scenario to `config/nova.dev.yaml`
3. Use in tests:
   ```python
   mock_data = MockData(dev_mode)
   scenario = mock_data.load_scenario("my_scenario")
   ```

### Performance Testing

1. Enable profiling:
   ```python
   with tools.profile("performance_test"):
       # Code to test
   ```

2. View results:
   ```bash
   poetry run python -m nova.dev.profile_viewer
   ```

### Debugging

1. Set breakpoint:
   ```python
   breakpoint()  # Python's built-in debugger
   ```

2. Or use VS Code:
   - Add debug configuration for port 5678
   - Start debugger
   - Set breakpoints in VS Code

## Best Practices

1. Development Mode
   - Always use dev config in development
   - Don't commit dev mode changes
   - Keep mock data up to date

2. Performance
   - Profile slow operations
   - Use mock data for large datasets
   - Monitor memory usage

3. Testing
   - Add mock scenarios for edge cases
   - Use dev tools in tests
   - Keep mock responses realistic

4. Debugging
   - Use debug logging
   - Profile before optimizing
   - Check metrics UI for issues 