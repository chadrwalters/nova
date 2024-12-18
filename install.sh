#!/bin/bash

# install.sh - Set up Nova Document Processor

set -e  # Exit on error

# Required files
REQUIRED_FILES=(
    ".env.template"
    "pyproject.toml"
    "config/default_config.yaml"
    ".cursorrules"
)

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$timestamp] $level: $message"
}

# Check required files
log "INFO" "Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log "ERROR" "Required file not found: $file"
        exit 1
    fi
done

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    log "INFO" "Creating .env from template..."
    cp .env.template .env
    
    # Set default NOVA_BASE_DIR if not already set
    DEFAULT_BASE_DIR="${HOME}/Documents/Nova"
    log "INFO" "Setting default NOVA_BASE_DIR to: ${DEFAULT_BASE_DIR}"
    sed -i.bak "s|NOVA_BASE_DIR=\"\${HOME}/Documents/Nova\"|NOVA_BASE_DIR=\"${DEFAULT_BASE_DIR}\"|" .env
    rm -f .env.bak
fi

# Check for Poetry
if ! command -v poetry &> /dev/null; then
    log "INFO" "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Update poetry.lock if needed
if [ ! -f poetry.lock ] || [ pyproject.toml -nt poetry.lock ]; then
    log "INFO" "Updating poetry.lock..."
    poetry lock --no-update
fi

# Install Python dependencies
log "INFO" "Installing Python dependencies..."
poetry install

# Install system dependencies based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    log "INFO" "Installing macOS system dependencies..."
    if ! command -v brew &> /dev/null; then
        log "ERROR" "Homebrew is required. Please install from https://brew.sh"
        exit 1
    fi
    for pkg in poppler tesseract; do
        if ! brew list $pkg &>/dev/null; then
            log "INFO" "Installing $pkg..."
            brew install $pkg
        fi
    done
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    log "INFO" "Installing Linux system dependencies..."
    sudo apt-get update
    sudo apt-get install -y poppler-utils tesseract-ocr
fi

# Source environment variables
source .env

# Expand environment variables
export NOVA_BASE_DIR="${NOVA_BASE_DIR:-${HOME}/Documents/Nova}"
export NOVA_INPUT_DIR="${NOVA_INPUT_DIR:-${NOVA_BASE_DIR}/_NovaInput}"
export NOVA_OUTPUT_DIR="${NOVA_OUTPUT_DIR:-${NOVA_BASE_DIR}/_Nova}"
export NOVA_CONFIG_DIR="${NOVA_CONFIG_DIR:-${NOVA_BASE_DIR}/_NovaConfig}"
export NOVA_PROCESSING_DIR="${NOVA_PROCESSING_DIR:-${NOVA_BASE_DIR}/_NovaProcessing}"
export NOVA_PHASE_MARKDOWN_PARSE="${NOVA_PHASE_MARKDOWN_PARSE:-${NOVA_PROCESSING_DIR}/01_markdown_parse}"
export NOVA_PHASE_MARKDOWN_CONSOLIDATE="${NOVA_PHASE_MARKDOWN_CONSOLIDATE:-${NOVA_PROCESSING_DIR}/02_markdown_consolidate}"
export NOVA_PHASE_PDF_GENERATE="${NOVA_PHASE_PDF_GENERATE:-${NOVA_PROCESSING_DIR}/03_pdf_generate}"
export NOVA_TEMP_DIR="${NOVA_TEMP_DIR:-${NOVA_PROCESSING_DIR}/temp}"
export NOVA_OFFICE_ASSETS_DIR="${NOVA_OFFICE_ASSETS_DIR:-${NOVA_BASE_DIR}/_NovaAssets}"
export NOVA_OFFICE_IMAGES_DIR="${NOVA_OFFICE_IMAGES_DIR:-${NOVA_OFFICE_ASSETS_DIR}/images}"
export NOVA_OFFICE_TEMP_DIR="${NOVA_OFFICE_TEMP_DIR:-${NOVA_PROCESSING_DIR}/temp_office}"

# Validate required environment variables
REQUIRED_VARS=(
    "NOVA_BASE_DIR"
    "NOVA_INPUT_DIR"
    "NOVA_OUTPUT_DIR"
    "NOVA_CONFIG_DIR"
    "NOVA_PROCESSING_DIR"
    "NOVA_PHASE_MARKDOWN_PARSE"
    "NOVA_PHASE_MARKDOWN_CONSOLIDATE"
    "NOVA_PHASE_PDF_GENERATE"
    "NOVA_TEMP_DIR"
    "NOVA_OFFICE_ASSETS_DIR"
    "NOVA_OFFICE_IMAGES_DIR"
)

log "INFO" "Validating environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log "ERROR" "Required environment variable $var is not set"
        exit 1
    fi
done

# Create directory structure
log "INFO" "Creating directory structure..."
# Ensure NOVA_BASE_DIR is set
if [ -z "$NOVA_BASE_DIR" ]; then
    log "ERROR" "NOVA_BASE_DIR is not set in .env"
    exit 1
fi

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
    if [ -z "$dir" ]; then
        log "ERROR" "Empty directory path"
        continue
    fi
    if [ ! -d "$dir" ]; then
        log "INFO" "Creating directory: ${dir}"
        mkdir -p "$dir"
        chmod 755 "$dir"
    fi
done

# Ensure config directory exists and has default config
if [ ! -f "${NOVA_CONFIG_DIR}/default_config.yaml" ]; then
    log "INFO" "Copying default configuration..."
    cp config/default_config.yaml "${NOVA_CONFIG_DIR}/"
fi

# Verify installation
log "INFO" "Verifying installation..."
if poetry run python -c "
    import markdown_it, mdit_py_plugins, structlog, pydantic, typer
    import json, yaml, magic, psutil
    print('All dependencies installed successfully')
"; then
    log "INFO" "Installation successful"
    log "INFO" "Directory structure created at: ${NOVA_BASE_DIR}"
    log "INFO" "Place markdown files in: ${NOVA_INPUT_DIR}"
    log "INFO" "Output will be generated in: ${NOVA_OUTPUT_DIR}"
else
    log "ERROR" "Installation verification failed"
    exit 1
fi