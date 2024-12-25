#!/bin/bash

# Source environment variables
source .env

# Verify directories
echo -e "\nVerifying directories..."

# Create Phase 1 Output Directories
echo -e "\nCreating Phase 1 Output Directories..."
mkdir -p "$NOVA_PHASE_MARKDOWN_PARSE"
mkdir -p "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_AGGREGATE"
mkdir -p "$NOVA_PHASE_MARKDOWN_SPLIT"

# Create Image Directories
echo -e "\nCreating Image Directories..."
mkdir -p "$NOVA_ORIGINAL_IMAGES_DIR"
mkdir -p "$NOVA_PROCESSED_IMAGES_DIR"
mkdir -p "$NOVA_IMAGE_METADATA_DIR"
mkdir -p "$NOVA_IMAGE_CACHE_DIR"

# Create Office Directories
echo -e "\nCreating Office Directories..."
mkdir -p "$NOVA_OFFICE_ASSETS_DIR"
mkdir -p "$NOVA_OFFICE_TEMP_DIR"

# Check Poetry installation
echo -e "\nChecking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed"
    exit 1
fi
echo "Poetry is installed"

# Check input files
echo -e "\nChecking input files..."
input_files=$(find "$NOVA_INPUT_DIR" -name "*.md" | wc -l)
echo "Found $input_files markdown files"

# Run pipeline
echo -e "\nRunning pipeline..."
poetry run python -c "
import asyncio
from nova.main import process_documents

async def main():
    config = {
        'input_dir': '$NOVA_INPUT_DIR',
        'output_dir': '$NOVA_PHASE_MARKDOWN_PARSE'
    }
    success = await process_documents(config)
    if not success:
        print('Pipeline failed')
        exit(1)

asyncio.run(main())"

if [ $? -ne 0 ]; then
    echo -e "\nPipeline failed"
    exit 1
fi