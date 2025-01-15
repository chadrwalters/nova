#!/bin/bash

# Get the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set Nova root directory (parent of scripts)
NOVA_ROOT="$(dirname "$SCRIPT_DIR")"

# Set up Python environment
UV_PATH="$NOVA_ROOT/.venv/bin/uv"

# Change to project directory
cd "$NOVA_ROOT"

# Activate virtual environment
source "$NOVA_ROOT/.venv/bin/activate"

# Set up environment
export PYTHONPATH="$NOVA_ROOT"
export PYTHONUNBUFFERED=1
export NOVA_LOG_DIR="$NOVA_ROOT/.nova/logs"

# Ensure log directory exists
mkdir -p "$NOVA_LOG_DIR"

# Log startup
echo "Starting Nova MCP server..." >&2
echo "NOVA_ROOT: $NOVA_ROOT" >&2
echo "UV_PATH: $UV_PATH" >&2
echo "PWD: $(pwd)" >&2

# Run the server
exec "$UV_PATH" run python -m nova.cli.commands.nova_mcp_server
