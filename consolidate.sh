#!/bin/bash

# consolidate.sh - Process markdown files to PDF

set -e  # Exit on error
set -u  # Exit on undefined variable

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$timestamp] $level: $message"
}

# Load environment variables first
if [ ! -f .env ]; then
    log "ERROR" ".env file not found"
    exit 1
fi

log "INFO" "Loading environment variables"
set -a  # Mark all variables for export
source .env
set +a  # Stop marking for export

# Create required directories
log "INFO" "Creating required directories..."
for dir in \
    "$NOVA_BASE_DIR" \
    "$NOVA_INPUT_DIR" \
    "$NOVA_OUTPUT_DIR" \
    "$NOVA_CONFIG_DIR" \
    "$NOVA_PROCESSING_DIR" \
    "$NOVA_PHASE_MARKDOWN_PARSE" \
    "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
    "$NOVA_PHASE_PDF_GENERATE" \
    "$NOVA_TEMP_DIR" \
    "$NOVA_OFFICE_ASSETS_DIR" \
    "$NOVA_OFFICE_IMAGES_DIR"; do
    if [ ! -d "$dir" ]; then
        log "INFO" "Creating directory: $dir"
        mkdir -p "$dir"
        chmod 755 "$dir"
    fi
done

# Initialize variables with defaults if not set in .env
: "${NOVA_INPUT_DIR:="${NOVA_BASE_DIR}/_NovaInput"}"
: "${NOVA_OUTPUT_DIR:="${NOVA_BASE_DIR}/_Nova"}"
: "${NOVA_PROCESSING_DIR:="${NOVA_BASE_DIR}/_NovaProcessing"}"
: "${MAX_RETRIES:=3}"
: "${RETRY_DELAY:=1}"
: "${BACKOFF_FACTOR:=2}"
MONITOR_PID=""
LOCK_FILE="${NOVA_OUTPUT_DIR}/process.lock"

# Function declarations
check_disk_space() {
    local dir="$1"
    local available=$(df -P "$dir" | awk 'NR==2 {print $4}')
    local required=$((5 * 1024 * 1024))  # 5GB minimum
    if [ "$available" -lt "$required" ]; then
        log "ERROR" "Insufficient disk space in $dir. Required: 5GB, Available: $((available/1024/1024))GB"
        exit 1
    fi
}

resolve_safe_path() {
    local path="$1"
    if [ -L "$path" ]; then
        local real_path=$(readlink -f "$path")
        if [ "$real_path" != "${NOVA_INPUT_DIR}"* ] && [ "$real_path" != "${NOVA_OUTPUT_DIR}"* ]; then
            log "ERROR" "Symlink $path points outside allowed directories"
            exit 1
        fi
    fi
    echo "$path"
}

monitor_resources() {
    touch "${NOVA_PROCESSING_DIR}/.monitor"
    
    while true; do
        if [ ! -f "${NOVA_PROCESSING_DIR}/.monitor" ]; then
            break
        fi
        
        local pages_free=$(vm_stat | awk '/Pages free/ {gsub(/\./, "", $3); print $3}')
        local pages_speculative=$(vm_stat | awk '/Pages speculative/ {gsub(/\./, "", $3); print $3}')
        local mem_available=$(((pages_free + pages_speculative) * 4096 / 1024 / 1024))
        local min_required=32
        
        if [ "$mem_available" -lt "$min_required" ]; then
            log "WARNING" "Low memory available. Required: ${min_required}MB, Available: ${mem_available}MB"
            python3 -c "import gc; gc.collect()"
            sleep 2
        fi
        
        sleep 1
    done
}

cleanup() {
    log "INFO" "Cleaning up..."
    if [ ! -z "$MONITOR_PID" ]; then
        rm -f "${NOVA_PROCESSING_DIR}/.monitor"
        kill "$MONITOR_PID" 2>/dev/null || true
        wait "$MONITOR_PID" 2>/dev/null || true
    fi
    
    MONITOR_FILE="${NOVA_PROCESSING_DIR}/.monitor"
    LOCK_FILE="${NOVA_OUTPUT_DIR}/process.lock"
    
    [ -f "$MONITOR_FILE" ] && rm -f "$MONITOR_FILE"
    [ -f "$LOCK_FILE" ] && rm -f "$LOCK_FILE"
    log "INFO" "Removing process lock file"
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Define monitor and lock files at the top level
MONITOR_FILE="${NOVA_PROCESSING_DIR}/.monitor"
LOCK_FILE="${NOVA_OUTPUT_DIR}/process.lock"

# Start monitoring
monitor_resources &
MONITOR_PID=$!

# Create lock file
log "INFO" "Creating process lock file"
touch "$LOCK_FILE"

# Main script execution
log "INFO" "Starting document processing"

# Validate required environment variables
required_vars=(
    "NOVA_INPUT_DIR"
    "NOVA_OUTPUT_DIR"
    "NOVA_PHASE_MARKDOWN_PARSE"
    "NOVA_PHASE_MARKDOWN_CONSOLIDATE"
    "NOVA_PHASE_PDF_GENERATE"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        log "ERROR" "Required environment variable $var is not set"
        exit 1
    fi
    
    if [ ! -d "${!var}" ]; then
        log "INFO" "Creating directory ${!var}"
        mkdir -p "${!var}"
    fi
    
    if [ ! -w "${!var}" ]; then
        log "ERROR" "Directory ${!var} is not writable"
        exit 1
    fi
done

# Process files
if [ ! -d "${NOVA_INPUT_DIR}" ]; then
    log "ERROR" "Input directory ${NOVA_INPUT_DIR} does not exist"
    exit 1
fi

shopt -s nullglob
INPUT_FILES=("${NOVA_INPUT_DIR}"/*.md)
shopt -u nullglob

if [ ${#INPUT_FILES[@]} -eq 0 ]; then
    log "ERROR" "No markdown files found in ${NOVA_INPUT_DIR}"
    exit 1
fi

# Sort files
IFS=$'\n' INPUT_FILES=($(sort <<<"${INPUT_FILES[*]}"))

# Show files to be processed
log "INFO" "Starting processing of files:"
for file in "${INPUT_FILES[@]}"; do
    log "INFO" "  - $(basename "$file")"
done

# Run the pipeline phases
attempt=1
while [ $attempt -le $MAX_RETRIES ]; do
    log "INFO" "Processing attempt $attempt of $MAX_RETRIES..."
    
    # Phase 1: Markdown Parse
    log "INFO" "Running Phase 1: Markdown Parse"
    if ! PYTHONPATH="." poetry run python3 -m src.cli.main process-markdown \
        --input "$NOVA_INPUT_DIR" \
        --output "$NOVA_PHASE_MARKDOWN_PARSE" \
        --config config/default_config.yaml; then
        exit_code=$?
        log "ERROR" "Phase 1 failed"
        if [ $attempt -eq $MAX_RETRIES ]; then
            log "ERROR" "Processing failed after $MAX_RETRIES attempts"
            exit $exit_code
        fi
        delay=$((RETRY_DELAY * BACKOFF_FACTOR ** (attempt - 1)))
        log "INFO" "Retrying in $delay seconds..."
        sleep $delay
        ((attempt++))
        continue
    fi
    
    # Phase 2: Markdown Consolidate
    log "INFO" "Running Phase 2: Markdown Consolidate"
    if ! PYTHONPATH="." poetry run python3 -m src.cli.main consolidate \
        --input "$NOVA_PHASE_MARKDOWN_PARSE" \
        --output "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
        --config config/default_config.yaml; then
        exit_code=$?
        log "ERROR" "Phase 2 failed"
        if [ $attempt -eq $MAX_RETRIES ]; then
            log "ERROR" "Processing failed after $MAX_RETRIES attempts"
            exit $exit_code
        fi
        delay=$((RETRY_DELAY * BACKOFF_FACTOR ** (attempt - 1)))
        log "INFO" "Retrying in $delay seconds..."
        sleep $delay
        ((attempt++))
        continue
    fi
    
    # Phase 3: PDF Generate
    log "INFO" "Running Phase 3: PDF Generate"
    if ! PYTHONPATH="." poetry run python3 -m src.cli.main generate-pdf \
        --input "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
        --output "$NOVA_OUTPUT_DIR" \
        --config config/default_config.yaml; then
        exit_code=$?
        log "ERROR" "Phase 3 failed"
        if [ $attempt -eq $MAX_RETRIES ]; then
            log "ERROR" "Processing failed after $MAX_RETRIES attempts"
            exit $exit_code
        fi
        delay=$((RETRY_DELAY * BACKOFF_FACTOR ** (attempt - 1)))
        log "INFO" "Retrying in $delay seconds..."
        sleep $delay
        ((attempt++))
        continue
    fi
    
    log "INFO" "All phases completed successfully"
    break
done

log "INFO" "Processing completed successfully"
exit 0
