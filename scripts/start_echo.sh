#!/bin/bash

# Echo server startup script
NOVA_ROOT="/Users/chadwalters/source/nova"
UV_PATH="/Users/chadwalters/.local/bin/uv"

# Change to project directory
cd "$NOVA_ROOT"

# Set up environment
export PYTHONPATH="$NOVA_ROOT"
export PYTHONUNBUFFERED=1

# Run the server
exec "$UV_PATH" run python -m nova.examples.mcp.echo_server
