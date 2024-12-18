#!/bin/bash

# Exit on error
set -e

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is required but not installed. Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "Please update .env with your configuration"
    exit 1
fi

# Load environment variables
source .env

# Create required directories
echo "Creating required directories..."
mkdir -p "${NOVA_PROCESSING_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}/temp"
mkdir -p "${NOVA_PHASE_MARKDOWN_PARSE}"
mkdir -p "${NOVA_PROCESSING_DIR}/temp_office"

# Create image processing directories
echo "Creating image processing directories..."
mkdir -p "${NOVA_ORIGINAL_IMAGES_DIR}"
mkdir -p "${NOVA_PROCESSED_IMAGES_DIR}"
mkdir -p "${NOVA_IMAGE_METADATA_DIR}"
mkdir -p "${NOVA_IMAGE_CACHE_DIR}"

# Install dependencies using poetry
echo "Installing Python dependencies..."
poetry install --no-dev

# Set up pre-commit hooks for development if --dev flag is passed
if [ "$1" = "--dev" ]; then
    echo "Setting up development environment..."
    poetry install
    pre-commit install
fi

echo "Installation complete!"
echo "You can now use 'poetry run nova' to process documents"