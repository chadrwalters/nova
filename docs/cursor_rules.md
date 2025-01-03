# Cursor Rules for Nova

## Logging Configuration

### Rule: Use Environment Variables for Logging Control

Nova uses environment variables for logging configuration. The primary way to control logging output is through the `NOVA_LOG_LEVEL` environment variable.

**Correct Usage:**
```bash
# Set logging level before running the pipeline
export NOVA_LOG_LEVEL=DEBUG
./run_nova.sh

# Or set it inline
NOVA_LOG_LEVEL=DEBUG ./run_nova.sh
```

**Available Log Levels:**
- `ERROR`: Only show errors
- `WARNING`: Show warnings and errors (default)
- `INFO`: Show informational messages, warnings, and errors
- `DEBUG`: Show all debug information, informational messages, warnings, and errors

**Do Not:**
- Modify logging configuration in `nova.yaml` - it will be ignored
- Try to configure logging through code - use the environment variable
- Mix different logging configuration methods

**Why:**
- Consistent logging control across all components
- Easy to change logging level without modifying code or config files
- Follows the principle of configuration through environment variables 