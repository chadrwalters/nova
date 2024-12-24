#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Print step message
print_step() {
    echo -e "\n${YELLOW}$1${NC}"
}

# Print success message
print_success() {
    echo -e "${GREEN}$1${NC}"
}

# Print error message
print_error() {
    echo -e "${RED}$1${NC}"
}

# Check Python installation
print_step "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

python_version=$(python3 -V | cut -d' ' -f2)
required_version="3.10.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_error "Python 3.10 or higher is required"
    exit 1
fi

print_success "Python $python_version is installed"

# Check Poetry installation
print_step "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    print_step "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

print_success "Poetry is installed"

# Create .env file if it doesn't exist
print_step "Setting up environment..."
if [ ! -f .env ]; then
    cat > .env << EOL
# Nova environment configuration

# Base directories
NOVA_BASE_DIR=\${PWD}/data
NOVA_INPUT_DIR=\${NOVA_BASE_DIR}/input
NOVA_OUTPUT_DIR=\${NOVA_BASE_DIR}/output
NOVA_PROCESSING_DIR=\${NOVA_BASE_DIR}/processing
NOVA_TEMP_DIR=\${NOVA_BASE_DIR}/temp

# Phase directories
NOVA_PHASE_MARKDOWN_PARSE=\${NOVA_PROCESSING_DIR}/markdown_parse
NOVA_PHASE_MARKDOWN_CONSOLIDATE=\${NOVA_PROCESSING_DIR}/markdown_consolidate
NOVA_PHASE_MARKDOWN_AGGREGATE=\${NOVA_PROCESSING_DIR}/markdown_aggregate
NOVA_PHASE_MARKDOWN_SPLIT=\${NOVA_PROCESSING_DIR}/markdown_split

# Image directories
NOVA_ORIGINAL_IMAGES_DIR=\${NOVA_PROCESSING_DIR}/images/original
NOVA_PROCESSED_IMAGES_DIR=\${NOVA_PROCESSING_DIR}/images/processed
NOVA_IMAGE_METADATA_DIR=\${NOVA_PROCESSING_DIR}/images/metadata
NOVA_IMAGE_CACHE_DIR=\${NOVA_PROCESSING_DIR}/images/cache

# Office document directories
NOVA_OFFICE_ASSETS_DIR=\${NOVA_PROCESSING_DIR}/office/assets
NOVA_OFFICE_TEMP_DIR=\${NOVA_PROCESSING_DIR}/office/temp

# OpenAI configuration
OPENAI_API_KEY=your_api_key_here
EOL

    print_success "Created .env file"
else
    print_success ".env file already exists"
fi

# Create directory structure
print_step "Creating directory structure..."
source .env

mkdir -p "$NOVA_INPUT_DIR" \
         "$NOVA_OUTPUT_DIR" \
         "$NOVA_PROCESSING_DIR" \
         "$NOVA_TEMP_DIR" \
         "$NOVA_PHASE_MARKDOWN_PARSE" \
         "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
         "$NOVA_PHASE_MARKDOWN_AGGREGATE" \
         "$NOVA_PHASE_MARKDOWN_SPLIT" \
         "$NOVA_ORIGINAL_IMAGES_DIR" \
         "$NOVA_PROCESSED_IMAGES_DIR" \
         "$NOVA_IMAGE_METADATA_DIR" \
         "$NOVA_IMAGE_CACHE_DIR" \
         "$NOVA_OFFICE_ASSETS_DIR" \
         "$NOVA_OFFICE_TEMP_DIR"

print_success "Directory structure created"

# Install dependencies
print_step "Installing dependencies..."
poetry install

print_success "Dependencies installed"

# Final instructions
print_step "Installation complete!"
echo -e "\nTo get started:"
echo -e "1. Edit .env file and set your OpenAI API key"
echo -e "2. Place markdown files in ${YELLOW}$NOVA_INPUT_DIR${NC}"
echo -e "3. Run ${YELLOW}poetry run nova --help${NC} to see available commands"