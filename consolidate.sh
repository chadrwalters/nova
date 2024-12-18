#!/bin/bash

# Nova Document Processor - Markdown Parse Phase
# This script handles the markdown parsing phase of the document processing pipeline

# Exit on error
set -e

# Source environment variables
if [ -f .env ]; then
    source .env
fi

# Configuration
MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Validate required environment variables
required_vars=(
    "NOVA_BASE_DIR"
    "NOVA_INPUT_DIR"
    "NOVA_OUTPUT_DIR"
    "NOVA_CONFIG_DIR"
    "NOVA_PROCESSING_DIR"
    "NOVA_TEMP_DIR"
    "NOVA_PHASE_MARKDOWN_PARSE"
    "NOVA_OFFICE_ASSETS_DIR"
    "NOVA_OFFICE_TEMP_DIR"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        log "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Create required directories
for dir in "${required_vars[@]}"; do
    if [ ! -d "${!dir}" ]; then
        mkdir -p "${!dir}"
        log "INFO: Created directory ${!dir}"
    fi
done

# Run the processor once without retries since we now handle file-level errors gracefully
log "INFO: Running Markdown Parse Phase"

NOVA_BASE_DIR="$NOVA_BASE_DIR" \
NOVA_INPUT_DIR="$NOVA_INPUT_DIR" \
NOVA_OUTPUT_DIR="$NOVA_OUTPUT_DIR" \
NOVA_CONFIG_DIR="$NOVA_CONFIG_DIR" \
NOVA_PROCESSING_DIR="$NOVA_PROCESSING_DIR" \
NOVA_TEMP_DIR="$NOVA_TEMP_DIR" \
NOVA_PHASE_MARKDOWN_PARSE="$NOVA_PHASE_MARKDOWN_PARSE" \
NOVA_OFFICE_ASSETS_DIR="$NOVA_OFFICE_ASSETS_DIR" \
NOVA_OFFICE_TEMP_DIR="$NOVA_OFFICE_TEMP_DIR" \
poetry run python -m src.cli.main "$NOVA_INPUT_DIR"

exit_code=$?

case $exit_code in
    0)
        log "INFO: Processing completed successfully"
        exit 0
        ;;
    1)
        log "ERROR: Critical error occurred during processing"
        exit 1
        ;;
    2)
        log "INFO: Processing completed with warnings"
        exit 0
        ;;
    *)
        log "ERROR: Unknown error occurred (exit code: $exit_code)"
        exit 1
        ;;
esac 