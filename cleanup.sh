#!/bin/bash

# Set default values
ALL_FLAG=false
PROCESSING_FLAG=false

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base directory for Nova
NOVA_BASE_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs"

# Logging functions
log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

# Function to clean processing directory
clean_processing() {
    local processing_dir="$NOVA_BASE_DIR/_NovaProcessing"
    if [ -d "$processing_dir" ]; then
        rm -rf "$processing_dir"/*
        if [ $? -eq 0 ]; then
            log_success "Processing directory cleaned successfully"
        else
            log_error "Failed to clean processing directory"
            return 1
        fi
    else
        log_success "Processing directory already clean"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            ALL_FLAG=true
            shift
            ;;
        -p|--processing)
            PROCESSING_FLAG=true
            shift
            ;;
        -h|--help)
            echo "Usage: cleanup.sh [-a|--all] [-p|--processing]"
            echo "Options:"
            echo "  -a, --all          Clean everything"
            echo "  -p, --processing   Clean processing directory"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# If no flags are set, show help
if [ "$ALL_FLAG" = false ] && [ "$PROCESSING_FLAG" = false ]; then
    echo "No cleanup options specified"
    echo "Use -h or --help for usage information"
    exit 1
fi

# Perform cleanup based on flags
SUCCESS=true

if [ "$ALL_FLAG" = true ] || [ "$PROCESSING_FLAG" = true ]; then
    clean_processing || SUCCESS=false
fi

if [ "$SUCCESS" = true ]; then
    log_success "All cleanup operations completed successfully"
    exit 0
else
    log_error "Some cleanup operations failed"
    exit 1
fi 