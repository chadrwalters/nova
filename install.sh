#!/bin/bash

# Exit on error
set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print status with color
print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Check Python installation
if ! command -v python3 &> /dev/null; then
    print_status "$RED" "✗ Error: Python 3 is required but not installed"
    exit 1
fi

# Check Poetry installation and install if needed
if ! command -v poetry &> /dev/null; then
    print_status "$YELLOW" "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    
    # Get base directory from user or use default
    read -p "Enter base directory for Nova (default: ${HOME}/Library/Mobile Documents/com~apple~CloudDocs): " base_dir
    base_dir=${base_dir:-"${HOME}/Library/Mobile Documents/com~apple~CloudDocs"}
    
    # Set up environment variables
    cat > .env << EOL
# Base directories
NOVA_BASE_DIR="$base_dir"
NOVA_INPUT_DIR="\${NOVA_BASE_DIR}/_NovaInput"
NOVA_OUTPUT_DIR="\${NOVA_BASE_DIR}/_NovaOutput"
NOVA_PROCESSING_DIR="\${NOVA_BASE_DIR}/_NovaProcessing"
NOVA_TEMP_DIR="\${NOVA_PROCESSING_DIR}/temp"

# Phase directories
NOVA_PHASE_MARKDOWN_PARSE="\${NOVA_PROCESSING_DIR}/phases/markdown_parse"

# Image directories
NOVA_ORIGINAL_IMAGES_DIR="\${NOVA_PROCESSING_DIR}/images/original"
NOVA_PROCESSED_IMAGES_DIR="\${NOVA_PROCESSING_DIR}/images/processed"
NOVA_IMAGE_METADATA_DIR="\${NOVA_PROCESSING_DIR}/images/metadata"
NOVA_IMAGE_CACHE_DIR="\${NOVA_PROCESSING_DIR}/images/cache"

# Office directories
NOVA_OFFICE_ASSETS_DIR="\${NOVA_PROCESSING_DIR}/office/assets"
NOVA_OFFICE_TEMP_DIR="\${NOVA_PROCESSING_DIR}/office/temp"

# OpenAI API configuration
OPENAI_API_KEY="your-api-key-here"

# Processing configuration
NOVA_LOG_LEVEL="INFO"
NOVA_MAX_WORKERS=4
NOVA_BATCH_SIZE=100
NOVA_ENABLE_IMAGE_PROCESSING=true
NOVA_ENABLE_OFFICE_PROCESSING=true
NOVA_ENABLE_CACHE=true
EOL

    echo ".env file created successfully"
fi

# Install dependencies
print_status "$CYAN" "Installing Python dependencies..."
poetry install

# Set up pre-commit hooks for development if --dev flag is passed
if [ "$1" = "--dev" ]; then
    print_status "$CYAN" "Setting up development environment..."
    poetry install
    pre-commit install
fi

print_status "$GREEN" "✓ Installation complete!"