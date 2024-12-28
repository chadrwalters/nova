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
    # Run cleanup script with force option
    ./cleanup.sh force-clean
    exit "$exit_code"
}

on_interrupt() {
    log_warning "Received interrupt signal"
    ./cleanup.sh force-clean
    exit 130
}

# Verify environment
verify_environment() {
    log_info "Verifying environment..."
    
    # Check required environment variables
    local required_vars=(
        "NOVA_BASE_DIR"
        "NOVA_INPUT_DIR"
        "NOVA_OUTPUT_DIR"
        "NOVA_PROCESSING_DIR"
        "NOVA_TEMP_DIR"
        "NOVA_STATE_DIR"
        "NOVA_LOG_LEVEL"
        "NOVA_MAX_WORKERS"
        "NOVA_BATCH_SIZE"
        "NOVA_ENABLE_CACHE"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable not set: $var"
            return 1
        fi
    done
    
    # Verify Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not found"
        return 1
    fi
    
    # Verify poetry installation
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry is required but not found"
        return 1
    fi
    
    log_info "Environment verified"
    return 0
}

# Verify input files
verify_input() {
    log_info "Verifying input files..."
    
    # Check input directory exists and contains markdown files
    if [ ! -d "$NOVA_INPUT_DIR" ]; then
        log_error "Input directory does not exist: $NOVA_INPUT_DIR"
        return 1
    fi
    
    # Count markdown files
    local md_count=$(find "$NOVA_INPUT_DIR" -type f -name "*.md" | wc -l)
    if [ "$md_count" -eq 0 ]; then
        log_warning "No markdown files found in input directory"
        return 1
    fi
    
    log_info "Found $md_count markdown files to process"
    return 0
}

# Run pipeline with progress monitoring
run_pipeline() {
    local config_file="${1:-config/pipeline_config.yaml}"
    log_info "Running consolidation pipeline..."
    
    # Verify config file exists
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    # Export additional environment variables
    export PYTHONPATH="src:${PYTHONPATH:-}"
    export NOVA_CONFIG_FILE="$config_file"
    
    # Run the async pipeline with progress monitoring
    log_info "Starting pipeline execution..."
    if ! python3 -m nova.cli.consolidate \
        --config "$config_file" \
        --log-level "${NOVA_LOG_LEVEL:-INFO}" \
        --show-progress \
        --monitor-resources; then
        log_error "Pipeline execution failed"
        return 1
    fi
    
    log_info "Pipeline execution completed successfully"
    return 0
}

# Verify pipeline output
verify_output() {
    log_info "Verifying pipeline output..."
    
    # Check output directory exists and contains expected files
    if [ ! -d "$NOVA_PHASE_MARKDOWN_PARSE" ]; then
        log_error "Output directory does not exist: $NOVA_PHASE_MARKDOWN_PARSE"
        return 1
    fi
    
    # Check if any markdown files were processed
    local markdown_files=("$NOVA_PHASE_MARKDOWN_PARSE"/*.md)
    if [ ${#markdown_files[@]} -eq 0 ]; then
        log_error "No markdown files found in output directory"
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    local config_file="${1:-config/pipeline_config.yaml}"
    
    log_info "Starting consolidation process..."
    
    # Run cleanup first
    log_info "Running cleanup..."
    if ! ./cleanup.sh clean; then
        log_error "Cleanup failed"
        exit 1
    fi
    
    # Verify environment
    if ! verify_environment; then
        log_error "Environment verification failed"
        exit 1
    fi
    
    # Verify input
    if ! verify_input; then
        log_error "Input verification failed"
        exit 1
    fi
    
    # Run pipeline
    if ! run_pipeline "$config_file"; then
        log_error "Pipeline execution failed"
        exit 1
    fi
    
    # Verify output
    if ! verify_output; then
        log_error "Output verification failed"
        exit 1
    fi
    
    log_info "Consolidation process completed successfully"
}

# Execute main function
main "$@"