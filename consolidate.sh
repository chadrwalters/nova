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

# Show help message
show_help() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -f, --force       Force processing of all files"
    echo "  -n, --dry-run     Show what would be done"
    echo "  -s, --show-state  Display current state"
    echo "  --scan            Show directory structure"
    echo "  --reset           Reset processing state"
    echo "  -h, --help        Show this help message"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
SHOW_STATE=false
SCAN=false
RESET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--show-state)
            SHOW_STATE=true
            shift
            ;;
        --scan)
            SCAN=true
            shift
            ;;
        --reset)
            RESET=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Load environment variables
print_step "Loading environment..."
if [ ! -f .env ]; then
    print_error ".env file not found"
    echo "Please run ./install.sh first"
    exit 1
fi

source .env

# Check required environment variables
required_vars=(
    "NOVA_BASE_DIR"
    "NOVA_INPUT_DIR"
    "NOVA_OUTPUT_DIR"
    "NOVA_PROCESSING_DIR"
    "NOVA_TEMP_DIR"
    "NOVA_PHASE_MARKDOWN_PARSE"
    "NOVA_PHASE_MARKDOWN_CONSOLIDATE"
    "NOVA_PHASE_MARKDOWN_AGGREGATE"
    "NOVA_PHASE_MARKDOWN_SPLIT"
    "NOVA_ORIGINAL_IMAGES_DIR"
    "NOVA_PROCESSED_IMAGES_DIR"
    "NOVA_IMAGE_METADATA_DIR"
    "NOVA_IMAGE_CACHE_DIR"
    "NOVA_OFFICE_ASSETS_DIR"
    "NOVA_OFFICE_TEMP_DIR"
    "OPENAI_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
        exit 1
    fi
done

print_success "Environment loaded"

# Check Poetry installation
print_step "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is not installed"
    echo "Please run ./install.sh first"
    exit 1
fi

print_success "Poetry is installed"

# Build command arguments
ARGS=""

if [ "$FORCE" = true ]; then
    ARGS="$ARGS --force"
fi

if [ "$DRY_RUN" = true ]; then
    ARGS="$ARGS --dry-run"
fi

# Handle special commands
if [ "$SHOW_STATE" = true ]; then
    print_step "Showing current state..."
    poetry run nova show-state
    exit 0
fi

if [ "$SCAN" = true ]; then
    print_step "Scanning directory structure..."
    poetry run nova scan
    exit 0
fi

if [ "$RESET" = true ]; then
    print_step "Resetting state..."
    poetry run nova reset-state
    exit 0
fi

# Check for input files
print_step "Checking input files..."
if [ ! -d "$NOVA_INPUT_DIR" ]; then
    print_error "Input directory not found: $NOVA_INPUT_DIR"
    exit 1
fi

INPUT_FILES=$(find "$NOVA_INPUT_DIR" -type f -name "*.md" | wc -l)
if [ "$INPUT_FILES" -eq 0 ]; then
    print_error "No markdown files found in input directory"
    exit 1
fi

print_success "Found $INPUT_FILES markdown files"

# Run pipeline
print_step "Running pipeline..."
poetry run nova process $ARGS

# Show completion message
if [ $? -eq 0 ]; then
    print_success "Pipeline completed successfully"
    echo -e "\nOutput files are in: ${YELLOW}$NOVA_OUTPUT_DIR${NC}"
else
    print_error "Pipeline failed"
    exit 1
fi