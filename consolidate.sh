#!/bin/bash

# Source environment variables
source .env

# Verify directories
echo -e "\nVerifying directories..."

# Create base directories
mkdir -p "${NOVA_INPUT_DIR}"
mkdir -p "${NOVA_OUTPUT_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}"
mkdir -p "${NOVA_TEMP_DIR}"
mkdir -p "${NOVA_STATE_DIR}"

# Create Phase 1 Output Directories
echo -e "\nCreating Phase 1 Output Directories..."
mkdir -p "${NOVA_PHASE_MARKDOWN_PARSE}"
mkdir -p "${NOVA_PHASE_MARKDOWN_CONSOLIDATE}"
mkdir -p "${NOVA_PHASE_MARKDOWN_AGGREGATE}"
mkdir -p "${NOVA_PHASE_MARKDOWN_SPLIT}"

# Create Image Directories
echo -e "\nCreating Image Directories..."
mkdir -p "${NOVA_ORIGINAL_IMAGES_DIR}"
mkdir -p "${NOVA_PROCESSED_IMAGES_DIR}"
mkdir -p "${NOVA_IMAGE_METADATA_DIR}"
mkdir -p "${NOVA_IMAGE_CACHE_DIR}"
mkdir -p "${NOVA_IMAGE_TEMP_DIR}"

# Create Office Directories
echo -e "\nCreating Office Directories..."
mkdir -p "${NOVA_OFFICE_ASSETS_DIR}"
mkdir -p "${NOVA_OFFICE_TEMP_DIR}"

# Check Poetry installation
echo -e "\nChecking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Please install Poetry first."
    exit 1
fi
echo "Poetry is installed"

# Check input files
echo -e "\nChecking input files..."
input_count=$(find "${NOVA_INPUT_DIR}" -name "*.md" | wc -l)
printf "Found %8d markdown files\n" "$input_count"

# Run pipeline
echo -e "\nRunning pipeline..."
poetry run python -c "
import asyncio
from nova.main import process_documents

async def main():
    success = await process_documents(
        input_dir='${NOVA_INPUT_DIR}',
        output_dir='${NOVA_OUTPUT_DIR}'
    )
    if not success:
        exit(1)

asyncio.run(main())
"

# Check exit code
if [ $? -ne 0 ]; then
    echo -e "\nPipeline failed"
    exit 1
fi

echo -e "\nPipeline completed successfully"