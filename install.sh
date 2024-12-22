#!/bin/bash

# Exit on error
set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print status with color
print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Print header
echo -e "${BLUE}${BOLD}───────────────────────────────────── Nova Installation ────────────────────────────────────${NC}\n"

# Check Python installation
print_status "$CYAN" "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_status "$RED" "✗ Error: Python 3 is required but not installed"
    exit 1
else
    python_version=$(python3 --version)
    print_status "$GREEN" "✓ Found $python_version"
fi

# Check Poetry installation and install if needed
print_status "$CYAN" "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    print_status "$YELLOW" "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    print_status "$GREEN" "✓ Poetry installed successfully"
else
    poetry_version=$(poetry --version)
    print_status "$GREEN" "✓ Found $poetry_version"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "$CYAN" "Creating .env file..."
    
    # Get base directory from user or use default
    echo -e "${DIM}Enter base directory for Nova${NC}"
    read -p "(default: ${HOME}/Library/Mobile Documents/com~apple~CloudDocs): " base_dir
    base_dir=${base_dir:-"${HOME}/Library/Mobile Documents/com~apple~CloudDocs"}
    
    print_status "$CYAN" "Generating environment configuration..."
    
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

    print_status "$GREEN" "✓ .env file created successfully"
    print_status "$YELLOW" "Note: Please update OPENAI_API_KEY in .env with your API key"
fi

# Install dependencies
print_status "$CYAN" "Installing Python dependencies..."
poetry install
print_status "$GREEN" "✓ Dependencies installed successfully"

echo
print_status "$GREEN" "✓ Installation complete!"
print_status "$CYAN" "You can now run the processor using: ./consolidate.sh"
echo