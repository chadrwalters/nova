#!/bin/bash

# Create base directories
mkdir -p "${NOVA_INPUT_DIR}"
mkdir -p "${NOVA_OUTPUT_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}"
mkdir -p "${NOVA_TEMP_DIR}"

# Create phase directories
mkdir -p "${NOVA_PHASE_MARKDOWN_PARSE}"

# Create image directories
mkdir -p "${NOVA_ORIGINAL_IMAGES_DIR}"
mkdir -p "${NOVA_PROCESSED_IMAGES_DIR}"
mkdir -p "${NOVA_IMAGE_METADATA_DIR}"
mkdir -p "${NOVA_IMAGE_CACHE_DIR}"

# Create office directories
mkdir -p "${NOVA_OFFICE_ASSETS_DIR}"
mkdir -p "${NOVA_OFFICE_TEMP_DIR}"

# Set proper permissions
chmod -R 755 "${NOVA_BASE_DIR}"

echo "Directory structure created successfully in ${NOVA_BASE_DIR}"