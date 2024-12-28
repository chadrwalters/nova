#!/bin/bash

# Exit on error and undefined variables
set -eu

# Trap errors and interrupts
trap 'on_error $?' ERR
trap 'on_interrupt' INT TERM

# Source environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Logging utilities with timestamps
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1" >&2
}

log_debug() {
    if [ "${NOVA_LOG_LEVEL:-INFO}" = "DEBUG" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEBUG] $1"
    fi
}

# Error handling
on_error() {
    local exit_code=$1
    log_error "Script failed with exit code: $exit_code"
    # Cleanup any temporary resources
    clean_temp_files force
    exit "$exit_code"
}

on_interrupt() {
    log_warning "Received interrupt signal"
    clean_temp_files force
    exit 130
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
    
    log_debug "Verifying directory: '$dir'"
    
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
            find "$dir" -type f -mtime +"$cleanup_age" -delete 2>/dev/null || true
        else
            # Linux: Use find with -atime
            find "$dir" -type f -atime +"$cleanup_age" -delete 2>/dev/null || true
        fi
    fi
}

# Clean state files
clean_state() {
    log_info "Cleaning state files..."
    
    # Clean state directory
    if [ -d "$NOVA_STATE_DIR" ]; then
        log_info "Cleaning state directory: $NOVA_STATE_DIR"
        # Remove all .state files but keep directory structure
        find "$NOVA_STATE_DIR" -type f -name "*.state" -delete 2>/dev/null || true
        # Remove empty directories
        find "$NOVA_STATE_DIR" -type d -empty -delete 2>/dev/null || true
    fi
    
    # Clean cache files older than 7 days
    if [ -d "$NOVA_IMAGE_CACHE_DIR" ]; then
        log_info "Cleaning old cache files..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            find "$NOVA_IMAGE_CACHE_DIR" -type f -mtime +7 -delete 2>/dev/null || true
        else
            find "$NOVA_IMAGE_CACHE_DIR" -type f -atime +7 -delete 2>/dev/null || true
        fi
    fi
}

# Clean monitoring files
clean_monitoring() {
    log_info "Cleaning monitoring files..."
    
    # Clean monitoring files from temp directory
    if [ -d "$NOVA_TEMP_DIR" ]; then
        find "$NOVA_TEMP_DIR" -type f -name "*.monitor" -delete 2>/dev/null || true
        find "$NOVA_TEMP_DIR" -type f -name "*.metrics" -delete 2>/dev/null || true
    fi
}

# Clean temporary files
clean_temp_files() {
    local force="${1:-false}"
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
            if [ "$force" = "force" ]; then
                rm -rf "${dir:?}"/* 2>/dev/null || true
            else
                # Only clean files older than 1 day
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    find "$dir" -type f -mtime +1 -delete 2>/dev/null || true
                else
                    find "$dir" -type f -atime +1 -delete 2>/dev/null || true
                fi
            fi
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

# Verify all required directories exist
verify_directories() {
    log_info "Verifying directory structure..."
    
    # Verify all directories
    local dirs=(
        "$NOVA_BASE_DIR"
        "$NOVA_INPUT_DIR"
        "$NOVA_OUTPUT_DIR"
        "$NOVA_PROCESSING_DIR"
        "$NOVA_TEMP_DIR"
        "$NOVA_STATE_DIR"
        "$NOVA_PHASE_MARKDOWN_PARSE"
        "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
        "$NOVA_PHASE_MARKDOWN_AGGREGATE"
        "$NOVA_PHASE_MARKDOWN_SPLIT"
        "$NOVA_ORIGINAL_IMAGES_DIR"
        "$NOVA_PROCESSED_IMAGES_DIR"
        "$NOVA_IMAGE_METADATA_DIR"
        "$NOVA_IMAGE_CACHE_DIR"
        "$NOVA_OFFICE_ASSETS_DIR"
        "$NOVA_OFFICE_TEMP_DIR"
    )
    
    for dir in "${dirs[@]}"; do
        if ! verify_dir "$dir" true 755; then
            log_error "Failed to verify directory: $dir"
            return 1
        fi
    done
    
    log_info "Directory structure verified"
}

# Main execution
main() {
    local command="${1:-clean}"
    
    log_info "Starting cleanup with command: $command"
    
    case "$command" in
        clean)
            verify_directories
            clean_temp_files
            clean_state
            clean_monitoring
            ;;
        force-clean)
            verify_directories
            clean_temp_files force
            clean_state
            clean_monitoring
            ;;
        verify)
            verify_directories
            ;;
        *)
            echo "Usage: $0 [clean|force-clean|verify]"
            exit 1
            ;;
    esac
    
    log_info "Cleanup completed successfully"
}

# Execute main function
main "$@" 