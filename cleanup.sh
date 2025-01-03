#!/bin/bash

# Set default values
ALL_FLAG=false
CACHE_FLAG=false
TEMP_FLAG=false
INTERRUPTED_FLAG=false
PROCESSING_FLAG=false

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging functions
log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

# Function to clean cache
clean_cache() {
    if [ -d ".cache" ]; then
        rm -rf .cache
        if [ $? -eq 0 ]; then
            log_success "Cache directory cleaned successfully"
        else
            log_error "Failed to clean cache directory"
            return 1
        fi
    else
        log_success "Cache directory already clean"
    fi
}

# Function to clean temp files
clean_temp() {
    local temp_files=(./*.tmp)
    if [ -e "${temp_files[0]}" ]; then
        rm -f ./*.tmp
        if [ $? -eq 0 ]; then
            log_success "Temporary files cleaned successfully"
        else
            log_error "Failed to clean temporary files"
            return 1
        fi
    else
        log_success "No temporary files to clean"
    fi
}

# Function to clean interrupted runs
clean_interrupted() {
    if [ -d "processing" ]; then
        rm -rf processing
        if [ $? -eq 0 ]; then
            log_success "Interrupted runs cleaned successfully"
        else
            log_error "Failed to clean interrupted runs"
            return 1
        fi
    else
        log_success "No interrupted runs to clean"
    fi
}

# Function to clean processing directory
clean_processing() {
    if [ -d "processing" ]; then
        rm -rf processing
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
        -c|--cache)
            CACHE_FLAG=true
            shift
            ;;
        -t|--temp)
            TEMP_FLAG=true
            shift
            ;;
        -i|--interrupted)
            INTERRUPTED_FLAG=true
            shift
            ;;
        -p|--processing)
            PROCESSING_FLAG=true
            shift
            ;;
        -h|--help)
            echo "Usage: cleanup.sh [-a|--all] [-c|--cache] [-t|--temp] [-i|--interrupted] [-p|--processing]"
            echo "Options:"
            echo "  -a, --all          Clean everything"
            echo "  -c, --cache        Clean cache directory"
            echo "  -t, --temp         Clean temporary files"
            echo "  -i, --interrupted  Clean interrupted runs"
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
if [ "$ALL_FLAG" = false ] && [ "$CACHE_FLAG" = false ] && [ "$TEMP_FLAG" = false ] && [ "$INTERRUPTED_FLAG" = false ] && [ "$PROCESSING_FLAG" = false ]; then
    echo "No cleanup options specified"
    echo "Use -h or --help for usage information"
    exit 1
fi

# Perform cleanup based on flags
SUCCESS=true

if [ "$ALL_FLAG" = true ] || [ "$CACHE_FLAG" = true ]; then
    clean_cache || SUCCESS=false
fi

if [ "$ALL_FLAG" = true ] || [ "$TEMP_FLAG" = true ]; then
    clean_temp || SUCCESS=false
fi

if [ "$ALL_FLAG" = true ] || [ "$INTERRUPTED_FLAG" = true ]; then
    clean_interrupted || SUCCESS=false
fi

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