#!/bin/bash

# Echo server startup script

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

# Set up environment
export PYTHONPATH="$NOVA_ROOT"
export PYTHONUNBUFFERED=1

# Run the server
exec uv run python -m nova.examples.mcp.echo_server
