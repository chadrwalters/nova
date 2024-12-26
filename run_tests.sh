#!/bin/bash

# Source environment variables
set -a  # Automatically export all variables
source .env
set +a  # Stop automatically exporting

# Add src directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests with pytest
echo "Running tests..."
poetry run pytest tests/ -v 