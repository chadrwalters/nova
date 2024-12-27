#!/bin/bash

# Source environment variables
source .env

# Validate environment variables
echo "Validating environment variables..."
if [ -z "$NOVA_BASE_DIR" ]; then
    echo "Error: NOVA_BASE_DIR not set"
    exit 1
fi

if [ -z "$NOVA_INPUT_DIR" ]; then
    echo "Error: NOVA_INPUT_DIR not set"
    exit 1
fi

if [ -z "$NOVA_PROCESSING_DIR" ]; then
    echo "Error: NOVA_PROCESSING_DIR not set"
    exit 1
fi

if [ -z "$NOVA_TEMP_DIR" ]; then
    echo "Error: NOVA_TEMP_DIR not set"
    exit 1
fi

# Print directories being used
echo "Using directories:"
echo "Base dir: $NOVA_BASE_DIR"
echo "Input dir: $NOVA_INPUT_DIR"
echo "Processing dir: $NOVA_PROCESSING_DIR"
echo "Temp dir: $NOVA_TEMP_DIR"

# Create required directories
echo "Creating required directories..."
mkdir -p "$NOVA_BASE_DIR"
mkdir -p "$NOVA_INPUT_DIR"
mkdir -p "$NOVA_PROCESSING_DIR"
mkdir -p "$NOVA_TEMP_DIR"

# Create phase directories
echo "Creating phase directories..."
mkdir -p "$NOVA_PHASE_MARKDOWN_PARSE"
mkdir -p "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_AGGREGATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_SPLIT"

# Create image directories
echo "Creating image directories..."
mkdir -p "$NOVA_ORIGINAL_IMAGES_DIR"
mkdir -p "$NOVA_PROCESSED_IMAGES_DIR"
mkdir -p "$NOVA_IMAGE_METADATA_DIR"
mkdir -p "$NOVA_IMAGE_CACHE_DIR"
mkdir -p "$NOVA_IMAGE_TEMP_DIR"

# Create office directories
echo "Creating office directories..."
mkdir -p "$NOVA_OFFICE_ASSETS_DIR"
mkdir -p "$NOVA_OFFICE_TEMP_DIR"

# Verify directories exist
echo "Verifying directories..."
if [ ! -d "$NOVA_BASE_DIR" ]; then
    echo "Error: Base directory does not exist: $NOVA_BASE_DIR"
    exit 1
fi

if [ ! -d "$NOVA_INPUT_DIR" ]; then
    echo "Error: Input directory does not exist: $NOVA_INPUT_DIR"
    exit 1
fi

if [ ! -d "$NOVA_PROCESSING_DIR" ]; then
    echo "Error: Processing directory does not exist: $NOVA_PROCESSING_DIR"
    exit 1
fi

if [ ! -d "$NOVA_TEMP_DIR" ]; then
    echo "Error: Temp directory does not exist: $NOVA_TEMP_DIR"
    exit 1
fi

# Export environment variables
export NOVA_BASE_DIR
export NOVA_INPUT_DIR
export NOVA_OUTPUT_DIR
export NOVA_PROCESSING_DIR
export NOVA_TEMP_DIR
export NOVA_STATE_DIR
export NOVA_PHASE_MARKDOWN_PARSE
export NOVA_PHASE_MARKDOWN_CONSOLIDATE
export NOVA_PHASE_MARKDOWN_AGGREGATE
export NOVA_PHASE_MARKDOWN_SPLIT
export NOVA_ORIGINAL_IMAGES_DIR
export NOVA_PROCESSED_IMAGES_DIR
export NOVA_IMAGE_METADATA_DIR
export NOVA_IMAGE_CACHE_DIR
export NOVA_IMAGE_TEMP_DIR
export NOVA_OFFICE_ASSETS_DIR
export NOVA_OFFICE_TEMP_DIR
export OPENAI_API_KEY
export XAI_API_KEY
export XAI_CACHE_DIR
export NOVA_LOG_LEVEL
export NOVA_MAX_WORKERS
export NOVA_BATCH_SIZE
export NOVA_ENABLE_IMAGE_PROCESSING
export NOVA_ENABLE_OFFICE_PROCESSING
export NOVA_ENABLE_CACHE

# Run consolidation pipeline
echo "Running consolidation pipeline..."
python -m nova.cli.consolidate --config config/pipeline_config.yaml --log-level INFO