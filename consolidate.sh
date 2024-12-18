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

# Main processing loop
while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$SUCCESS" = false ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    log "INFO: Processing attempt $RETRY_COUNT of $MAX_RETRIES..."
    log "INFO: Running Markdown Parse Phase"
    
    if NOVA_BASE_DIR="$NOVA_BASE_DIR" \
       NOVA_INPUT_DIR="$NOVA_INPUT_DIR" \
       NOVA_OUTPUT_DIR="$NOVA_OUTPUT_DIR" \
       NOVA_CONFIG_DIR="$NOVA_CONFIG_DIR" \
       NOVA_PROCESSING_DIR="$NOVA_PROCESSING_DIR" \
       NOVA_TEMP_DIR="$NOVA_TEMP_DIR" \
       NOVA_PHASE_MARKDOWN_PARSE="$NOVA_PHASE_MARKDOWN_PARSE" \
       NOVA_OFFICE_ASSETS_DIR="$NOVA_OFFICE_ASSETS_DIR" \
       NOVA_OFFICE_TEMP_DIR="$NOVA_OFFICE_TEMP_DIR" \
       poetry run python -m src.cli.main "$NOVA_INPUT_DIR"; then
        SUCCESS=true
        break
    else
        log "ERROR: Processing failed"
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            WAIT_TIME=$((RETRY_COUNT))
            log "INFO: Retrying in $WAIT_TIME seconds..."
            sleep $WAIT_TIME
        fi
    fi
done

if [ "$SUCCESS" = true ]; then
    log "INFO: Processing completed successfully"
    exit 0
else
    log "ERROR: Processing failed after $MAX_RETRIES attempts"
    exit 1
fi 