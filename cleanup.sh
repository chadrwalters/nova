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
            # Cleanup handled by Python code
        fi
    fi
    
    # Check free space
    if [ -n "$min_free" ]; then
        free_space=$(get_free_space "$dir")
        if [ "$free_space" -lt "$min_free" ]; then
            log_warning "Low disk space on $dir (${free_space}MB < ${min_free}MB)"
            # Cleanup handled by Python code
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

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    # Base directories
    verify_dir "${NOVA_BASE_DIR}"
    verify_dir "${NOVA_INPUT_DIR}"
    verify_dir "${NOVA_OUTPUT_DIR}"
    verify_dir "${NOVA_PROCESSING_DIR}"
    verify_dir "${NOVA_TEMP_DIR}" true 755 1024 1024 1  # 1GB limit, 1GB min free, 1 day cleanup
    verify_dir "${NOVA_STATE_DIR}" true 700             # Restricted permissions for state
    
    # Phase directories
    verify_dir "${NOVA_PHASE_MARKDOWN_PARSE}"
    verify_dir "${NOVA_PHASE_MARKDOWN_CONSOLIDATE}"
    verify_dir "${NOVA_PHASE_MARKDOWN_AGGREGATE}"
    verify_dir "${NOVA_PHASE_MARKDOWN_SPLIT}"
    
    # Image directories
    verify_dir "${NOVA_ORIGINAL_IMAGES_DIR}"
    verify_dir "${NOVA_PROCESSED_IMAGES_DIR}" true 755 2048  # 2GB limit
    verify_dir "${NOVA_IMAGE_METADATA_DIR}"
    verify_dir "${NOVA_IMAGE_CACHE_DIR}" true 755 1024 512 7  # 1GB limit, 512MB min free, 7 day cleanup
    
    # Office directories
    verify_dir "${NOVA_OFFICE_ASSETS_DIR}"
    verify_dir "${NOVA_OFFICE_TEMP_DIR}" true 755 1024 1024 1  # 1GB limit, 1GB min free, 1 day cleanup
    
    log_info "Directory creation complete"
}

# Verify directory structure
verify_structure() {
    log_info "Verifying directory structure..."
    
    # Base directories
    verify_dir "${NOVA_BASE_DIR}" false
    verify_dir "${NOVA_INPUT_DIR}" false
    verify_dir "${NOVA_OUTPUT_DIR}" false
    verify_dir "${NOVA_PROCESSING_DIR}" false
    verify_dir "${NOVA_TEMP_DIR}" false
    verify_dir "${NOVA_STATE_DIR}" false
    
    # Phase directories
    verify_dir "${NOVA_PHASE_MARKDOWN_PARSE}" false
    verify_dir "${NOVA_PHASE_MARKDOWN_CONSOLIDATE}" false
    verify_dir "${NOVA_PHASE_MARKDOWN_AGGREGATE}" false
    verify_dir "${NOVA_PHASE_MARKDOWN_SPLIT}" false
    
    # Image directories
    verify_dir "${NOVA_ORIGINAL_IMAGES_DIR}" false
    verify_dir "${NOVA_PROCESSED_IMAGES_DIR}" false
    verify_dir "${NOVA_IMAGE_METADATA_DIR}" false
    verify_dir "${NOVA_IMAGE_CACHE_DIR}" false
    
    # Office directories
    verify_dir "${NOVA_OFFICE_ASSETS_DIR}" false
    verify_dir "${NOVA_OFFICE_TEMP_DIR}" false
    
    log_info "Directory structure verification complete"
}

# Clean temporary files
clean_temp_files() {
    log_info "Cleaning temporary files..."
    
    # Clean temp directories with size and age limits
    verify_dir "${NOVA_TEMP_DIR}" true 755 1024 1024 1
    verify_dir "${NOVA_OFFICE_TEMP_DIR}" true 755 1024 1024 1
    verify_dir "${NOVA_IMAGE_CACHE_DIR}" true 755 1024 512 7
    
    log_info "Temporary files cleaned"
}

# Clean virtual environment
clean_venv() {
    log_info "Cleaning virtual environment..."
    
    # Deactivate virtual environment if active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
    fi
    
    # Remove virtual environment directories
    for venv_dir in .venv venv env; do
        if [ -d "$venv_dir" ]; then
            log_info "Removing virtual environment: $venv_dir"
            rm -rf "$venv_dir"
        fi
    done
    
    # Remove pyenv local version file
    if [ -f ".python-version" ]; then
        log_info "Removing .python-version file"
        rm -f ".python-version"
    fi
    
    # Remove poetry and pytest cache
    if [ -d ".pytest_cache" ]; then
        rm -rf ".pytest_cache"
    fi
    if [ -d ".coverage" ]; then
        rm -rf ".coverage"
    fi
    if [ -d ".poetry" ]; then
        rm -rf ".poetry"
    fi
    if [ -d "__pycache__" ]; then
        rm -rf "__pycache__"
    fi
    
    log_info "Virtual environment cleaned"
}

# Show directory status
show_status() {
    log_info "Directory Status:"
    printf "%-30s %10s %10s\n" "Directory" "Size (MB)" "Free (MB)"
    printf "%-30s %10s %10s\n" "---------" "---------" "---------"
    
    for dir in \
        "${NOVA_BASE_DIR}" \
        "${NOVA_INPUT_DIR}" \
        "${NOVA_OUTPUT_DIR}" \
        "${NOVA_PROCESSING_DIR}" \
        "${NOVA_TEMP_DIR}" \
        "${NOVA_STATE_DIR}" \
        "${NOVA_PHASE_MARKDOWN_PARSE}" \
        "${NOVA_PHASE_MARKDOWN_CONSOLIDATE}" \
        "${NOVA_PHASE_MARKDOWN_AGGREGATE}" \
        "${NOVA_PHASE_MARKDOWN_SPLIT}" \
        "${NOVA_ORIGINAL_IMAGES_DIR}" \
        "${NOVA_PROCESSED_IMAGES_DIR}" \
        "${NOVA_IMAGE_METADATA_DIR}" \
        "${NOVA_IMAGE_CACHE_DIR}" \
        "${NOVA_OFFICE_ASSETS_DIR}" \
        "${NOVA_OFFICE_TEMP_DIR}"
    do
        if [ -d "$dir" ]; then
            size=$(get_dir_size "$dir")
            free=$(get_free_space "$dir")
            printf "%-30s %10d %10d\n" "$dir" "$size" "$free"
        fi
    done
}

# Main execution
main() {
    local command="${1:-create}"
    
    case "$command" in
        create)
            create_directories
            ;;
        verify)
            verify_structure
            ;;
        clean)
            clean_temp_files
            ;;
        clean-venv)
            clean_venv
            ;;
        clean-all)
            clean_temp_files
            clean_venv
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 [create|verify|clean|clean-venv|clean-all|status]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@" 