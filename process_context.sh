#!/bin/bash

# Exit on error
set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Source environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Activate poetry environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run Nova pipeline
python -m nova.cli \
    --config "$SCRIPT_DIR/config/nova.yaml" \
    "$@" 