#!/bin/bash

# Source environment variables
set -a  # Automatically export all variables
source .env
set +a  # Stop automatically exporting

# Validate environment variables
echo "Validating environment variables..."
if [ -z "$NOVA_BASE_DIR" ]; then
    echo "Error: NOVA_BASE_DIR is not set"
    exit 1
fi

if [ -z "$NOVA_INPUT_DIR" ]; then
    echo "Error: NOVA_INPUT_DIR is not set"
    exit 1
fi

if [ -z "$NOVA_PROCESSING_DIR" ]; then
    echo "Error: NOVA_PROCESSING_DIR is not set"
    exit 1
fi

echo "Using directories:"
echo "Base dir: $NOVA_BASE_DIR"
echo "Input dir: $NOVA_INPUT_DIR"
echo "Processing dir: $NOVA_PROCESSING_DIR"
echo "Parse dir: $NOVA_PHASE_MARKDOWN_PARSE"

# Check if input directory exists
if [ ! -d "$NOVA_INPUT_DIR" ]; then
    echo "Error: Input directory $NOVA_INPUT_DIR does not exist"
    exit 1
fi

# Create required directories
echo "Creating required directories..."
mkdir -p "$NOVA_OUTPUT_DIR"
mkdir -p "$NOVA_PROCESSING_DIR"
mkdir -p "$NOVA_PROCESSING_DIR/phases"
mkdir -p "$NOVA_PHASE_MARKDOWN_PARSE"
mkdir -p "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_AGGREGATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_SPLIT"
mkdir -p "$NOVA_TEMP_DIR"
mkdir -p "$NOVA_ORIGINAL_IMAGES_DIR"
mkdir -p "$NOVA_PROCESSED_IMAGES_DIR"
mkdir -p "$NOVA_IMAGE_METADATA_DIR"
mkdir -p "$NOVA_IMAGE_CACHE_DIR"
mkdir -p "$NOVA_IMAGE_TEMP_DIR"
mkdir -p "$NOVA_OFFICE_ASSETS_DIR"
mkdir -p "$NOVA_OFFICE_TEMP_DIR"

# Verify directories were created
echo "Verifying directories..."
for dir in "$NOVA_PHASE_MARKDOWN_PARSE" "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" "$NOVA_PHASE_MARKDOWN_AGGREGATE" "$NOVA_PHASE_MARKDOWN_SPLIT"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Failed to create directory: $dir"
        exit 1
    fi
done

# Check input files
echo "Checking input files..."
markdown_files=$(find "$NOVA_INPUT_DIR" -name "*.md" | wc -l)
image_files=$(find "$NOVA_INPUT_DIR" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.heic" -o -name "*.heif" | wc -l)
document_files=$(find "$NOVA_INPUT_DIR" -type f -name "*.pdf" -o -name "*.docx" -o -name "*.xlsx" -o -name "*.txt" -o -name "*.csv" | wc -l)

echo "Found:"
echo "-        $markdown_files markdown files"
echo "-        $image_files image files"
echo "-        $document_files document files"

# Add src directory to Python path
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Install dependencies if needed
echo "Installing dependencies..."
poetry install

# Run pipeline
echo "Starting pipeline..."
poetry run python -m nova.main