#!/bin/bash

# Nova Cleanup Script
# Cleans up temporary files, cache, and optionally resets the processing directory

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
CONFIG_FILE="${SCRIPT_DIR}/config/nova.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Python virtual environment not found. Please run install.sh first."
        exit 1
    fi
}

# Get processing directory from config
get_processing_dir() {
    # Create Python script to get directory
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import os
import sys
import yaml
from pathlib import Path

try:
    with open(os.environ["CONFIG_FILE"]) as f:
        config = yaml.safe_load(f)
    
    base_dir = os.path.expandvars(config["base_dir"])
    cache_dir = os.path.expandvars(config["cache"]["dir"])
    processing_dir = os.path.expandvars(os.path.expanduser("${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaProcessing"))
    print(f"{base_dir}\n{cache_dir}\n{processing_dir}")
    
except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    sys.exit(1)
EOF

    # Run script
    export CONFIG_FILE="$CONFIG_FILE"
    source "${VENV_DIR}/bin/activate"
    local dirs=$(python "$temp_script")
    local status=$?
    deactivate
    rm "$temp_script"

    if [ $status -ne 0 ]; then
        log_error "Failed to get directories from config"
        exit 1
    fi

    echo "$dirs"
}

# Clean cache
clean_cache() {
    log_info "Cleaning cache..."

    local dirs=$(get_processing_dir)
    local cache_dir=$(echo "$dirs" | sed -n '2p')

    if [ -d "$cache_dir" ]; then
        rm -rf "${cache_dir:?}"/*
        log_success "Cache cleaned"
    else
        log_warning "Cache directory not found"
    fi
}

# Clean temporary files
clean_temp() {
    log_info "Cleaning temporary files..."

    local dirs=$(get_processing_dir)
    local base_dir=$(echo "$dirs" | sed -n '1p')

    # Clean temp files in all directories
    find "$base_dir" -name "*.tmp" -type f -delete
    find "$base_dir" -name "*.part" -type f -delete
    find "$base_dir" -name "*.processing" -type f -delete

    log_success "Temporary files cleaned"
}

# Clean interrupted runs
clean_interrupted() {
    log_info "Cleaning interrupted runs..."

    local dirs=$(get_processing_dir)
    local base_dir=$(echo "$dirs" | sed -n '1p')
    local lock_file="${base_dir}/.lock"

    if [ -f "$lock_file" ]; then
        log_warning "Found interrupted run. Cleaning up..."
        rm -f "$lock_file"
        
        # Clean partial files
        find "$base_dir" -name "*.part" -type f -delete
        find "$base_dir" -name "*.processing" -type f -delete
        
        log_success "Interrupted run cleaned"
    else
        log_info "No interrupted runs found"
    fi
}

# Clean processing directory
clean_processing() {
    log_info "Cleaning processing directory..."

    local dirs=$(get_processing_dir)
    local processing_dir=$(echo "$dirs" | sed -n '3p')

    if [ -d "$processing_dir" ]; then
        rm -rf "${processing_dir:?}"/*
        log_success "Processing directory cleaned"
    else
        log_warning "Processing directory not found"
    fi
}

# Reset processing directory
reset_processing() {
    local keep_original=$1
    local dirs=$(get_processing_dir)
    local base_dir=$(echo "$dirs" | sed -n '1p')
    local cache_dir=$(echo "$dirs" | sed -n '2p')

    log_warning "This will delete processed files and metadata."
    if [ "$keep_original" = "true" ]; then
        log_info "Original files will be preserved"
    else
        log_warning "Original files will also be deleted"
    fi
    
    log_warning "Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Resetting processing directory..."

        if [ "$keep_original" = "true" ]; then
            # Keep original files, delete cache
            if [ -d "$cache_dir" ]; then
                rm -rf "${cache_dir:?}"/*
            fi
        else
            # Delete everything in base dir except .gitkeep
            find "$base_dir" -mindepth 1 -not -name ".gitkeep" -delete
            # Also clean cache
            if [ -d "$cache_dir" ]; then
                rm -rf "${cache_dir:?}"/*
            fi
        fi

        log_success "Processing directory reset"
    else
        log_info "Reset cancelled"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  -c, --cache           Clean cache files
  -t, --temp           Clean temporary files
  -i, --interrupted    Clean interrupted runs
  -p, --processing    Clean processing directory
  -r, --reset         Reset processing directory
  -k, --keep-original  When resetting, keep original files
  -a, --all           Clean everything (cache, temp, interrupted, processing)
  -h, --help          Show this help message

Examples:
  $0 --cache          # Clean only cache
  $0 --temp           # Clean only temporary files
  $0 --all           # Clean everything except original files
  $0 --reset         # Reset entire processing directory
  $0 --reset --keep-original  # Reset but keep original files
EOF
}

# Main execution
main() {
    # Parse command line arguments
    local clean_cache_flag=0
    local clean_temp_flag=0
    local clean_interrupted_flag=0
    local clean_processing_flag=0
    local reset_flag=0
    local keep_original=false

    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    while [ $# -gt 0 ]; do
        case "$1" in
            -c|--cache)
                clean_cache_flag=1
                shift
                ;;
            -t|--temp)
                clean_temp_flag=1
                shift
                ;;
            -i|--interrupted)
                clean_interrupted_flag=1
                shift
                ;;
            -p|--processing)
                clean_processing_flag=1
                shift
                ;;
            -r|--reset)
                reset_flag=1
                shift
                ;;
            -k|--keep-original)
                keep_original=true
                shift
                ;;
            -a|--all)
                clean_cache_flag=1
                clean_temp_flag=1
                clean_interrupted_flag=1
                clean_processing_flag=1
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Check virtual environment
    check_venv

    # Execute cleanup based on flags
    if [ $clean_cache_flag -eq 1 ]; then
        clean_cache
    fi

    if [ $clean_temp_flag -eq 1 ]; then
        clean_temp
    fi

    if [ $clean_interrupted_flag -eq 1 ]; then
        clean_interrupted
    fi

    if [ $clean_processing_flag -eq 1 ]; then
        clean_processing
    fi

    if [ $reset_flag -eq 1 ]; then
        reset_processing "$keep_original"
    fi
}

# Run main function
main "$@" 