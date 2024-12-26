#!/bin/bash

# Exit on error
set -e

# Source environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Expand environment variables
NOVA_BASE_DIR=$(eval echo "$NOVA_BASE_DIR")
NOVA_INPUT_DIR=$(eval echo "$NOVA_INPUT_DIR")
NOVA_OUTPUT_DIR=$(eval echo "$NOVA_OUTPUT_DIR")
NOVA_PROCESSING_DIR=$(eval echo "$NOVA_PROCESSING_DIR")
NOVA_TEMP_DIR=$(eval echo "$NOVA_TEMP_DIR")
NOVA_STATE_DIR=$(eval echo "$NOVA_STATE_DIR")
NOVA_PHASE_MARKDOWN_PARSE=$(eval echo "$NOVA_PHASE_MARKDOWN_PARSE")
NOVA_PHASE_MARKDOWN_CONSOLIDATE=$(eval echo "$NOVA_PHASE_MARKDOWN_CONSOLIDATE")
NOVA_PHASE_MARKDOWN_AGGREGATE=$(eval echo "$NOVA_PHASE_MARKDOWN_AGGREGATE")
NOVA_PHASE_MARKDOWN_SPLIT=$(eval echo "$NOVA_PHASE_MARKDOWN_SPLIT")
NOVA_ORIGINAL_IMAGES_DIR=$(eval echo "$NOVA_ORIGINAL_IMAGES_DIR")
NOVA_PROCESSED_IMAGES_DIR=$(eval echo "$NOVA_PROCESSED_IMAGES_DIR")
NOVA_IMAGE_METADATA_DIR=$(eval echo "$NOVA_IMAGE_METADATA_DIR")
NOVA_IMAGE_CACHE_DIR=$(eval echo "$NOVA_IMAGE_CACHE_DIR")
NOVA_OFFICE_ASSETS_DIR=$(eval echo "$NOVA_OFFICE_ASSETS_DIR")
NOVA_OFFICE_TEMP_DIR=$(eval echo "$NOVA_OFFICE_TEMP_DIR")

# Logging utilities
log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_warning() {
    echo "[WARNING] $1" >&2
}

# Get directory size in MB
get_dir_size() {
    local dir="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        du -sm "$dir" | cut -f1
    else
        # Linux
        du -sm "$dir" --apparent-size | cut -f1
    fi
}

# Get free space in MB
get_free_space() {
    local dir="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        df -m "$dir" | tail -1 | awk '{print $4}'
    else
        # Linux
        df -m --output=avail "$dir" | tail -1 | tr -d ' '
    fi
}

# Directory verification/creation function
verify_dir() {
    local dir="$1"
    local create="${2:-true}"  # Default to true
    local perms="${3:-755}"    # Default to 755
    local max_size="${4:-}"    # Optional max size in MB
    local min_free="${5:-}"    # Optional min free space in MB
    local cleanup_age="${6:-}" # Optional cleanup age in days
    
    echo "DEBUG: Verifying directory: '$dir'"
    
    if [ -z "$dir" ]; then
        log_error "Empty directory path provided"
        return 1
    fi
    
    if [ ! -e "$dir" ]; then
        if [ "$create" = "true" ]; then
            log_info "Creating directory: $dir"
            mkdir -p "$dir"
        else
            log_error "Directory does not exist: $dir"
            return 1
        fi
    fi
    
    if [ ! -d "$dir" ]; then
        log_error "Path exists but is not a directory: $dir"
        return 1
    fi
    
    # Set permissions
    chmod "$perms" "$dir"
    
    # Verify writability
    if [ ! -w "$dir" ]; then
        log_error "Directory is not writable: $dir"
        return 1
    fi
    
    # Check size limit
    if [ -n "$max_size" ]; then
        current_size=$(get_dir_size "$dir")
        if [ "$current_size" -gt "$max_size" ]; then
            log_warning "Directory $dir exceeds size limit (${current_size}MB > ${max_size}MB)"
        fi
    fi
    
    # Check free space
    if [ -n "$min_free" ]; then
        free_space=$(get_free_space "$dir")
        if [ "$free_space" -lt "$min_free" ]; then
            log_warning "Low disk space on $dir (${free_space}MB < ${min_free}MB)"
        fi
    fi
    
    # Clean old files
    if [ -n "$cleanup_age" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS: Use find with -mtime
            find "$dir" -type f -mtime +"$cleanup_age" -delete
        else
            # Linux: Use find with -atime
            find "$dir" -type f -atime +"$cleanup_age" -delete
        fi
    fi
}

# Clean temporary files
clean_temp_files() {
    log_info "Cleaning temporary files and processing directories..."
    
    # Clean temp directories with size and age limits
    verify_dir "$NOVA_TEMP_DIR" true 755 1024 1024 1
    verify_dir "$NOVA_OFFICE_TEMP_DIR" true 755 1024 1024 1
    verify_dir "$NOVA_IMAGE_CACHE_DIR" true 755 1024 512 7
    
    # Clean all processing directories
    log_info "Cleaning processing directories..."
    
    # Phase directories
    for dir in \
        "$NOVA_PHASE_MARKDOWN_PARSE" \
        "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
        "$NOVA_PHASE_MARKDOWN_AGGREGATE" \
        "$NOVA_PHASE_MARKDOWN_SPLIT"
    do
        if [ -d "$dir" ]; then
            log_info "Cleaning directory: $dir"
            rm -rf "${dir:?}"/* 2>/dev/null || true
        fi
    done
    
    # Image processing directories
    for dir in \
        "$NOVA_PROCESSED_IMAGES_DIR" \
        "$NOVA_IMAGE_METADATA_DIR" \
        "$NOVA_IMAGE_CACHE_DIR"
    do
        if [ -d "$dir" ]; then
            log_info "Cleaning directory: $dir"
            rm -rf "${dir:?}"/* 2>/dev/null || true
        fi
    done
    
    # Office processing directories
    for dir in \
        "$NOVA_OFFICE_ASSETS_DIR" \
        "$NOVA_OFFICE_TEMP_DIR"
    do
        if [ -d "$dir" ]; then
            log_info "Cleaning directory: $dir"
            rm -rf "${dir:?}"/* 2>/dev/null || true
        fi
    done
    
    log_info "All processing directories cleaned"
}

# Main execution
main() {
    local command="${1:-create}"
    
    case "$command" in
        clean)
            clean_temp_files
            ;;
        *)
            echo "Usage: $0 [clean]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@" 