#!/bin/bash

# consolidate.sh - Process markdown files to PDF

set -e  # Exit on error
set -u  # Exit on undefined variable

# Load environment variables
source .env

# Run the pipeline
poetry run python -m src.cli.main process

# Print success message
echo "✓ Processing complete!"
echo "Output: ${NOVA_OUTPUT_DIR}/output.pdf"
