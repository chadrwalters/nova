#!/bin/bash

# Get the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NOVA_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment configuration
if [ -f "$NOVA_ROOT/.env.local" ]; then
    source "$NOVA_ROOT/.env.local"
elif [ -f "$NOVA_ROOT/.env" ]; then
    source "$NOVA_ROOT/.env"
fi

# Change to project directory
cd "$NOVA_ROOT"

# Activate virtual environment
source .venv/bin/activate

# Set up environment
export PYTHONPATH="$NOVA_ROOT"
export PYTHONUNBUFFERED=1

# Default paths - use environment variables with fallbacks
NOVA_HOME="${NOVA_HOME:-.nova}"
NOVA_LOCAL="${NOVA_LOCAL:-.nova}"
export NOVA_LOG_DIR="$NOVA_LOCAL/logs"

# Ensure log directory exists
mkdir -p "$NOVA_LOG_DIR"

# Log startup
echo "Starting Nova MCP server..." >&2
echo "NOVA_ROOT: $NOVA_ROOT" >&2
echo "NOVA_HOME: $NOVA_HOME" >&2
echo "NOVA_LOCAL: $NOVA_LOCAL" >&2
echo "NOVA_LOG_DIR: $NOVA_LOG_DIR" >&2
echo "PWD: $(pwd)" >&2
echo "VIRTUAL_ENV: $VIRTUAL_ENV" >&2

# Run the server
exec uv run python -m nova.cli.commands.nova_mcp_server
