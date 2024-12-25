#!/bin/bash

# Exit on error
set -e

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

# Check and setup pyenv
setup_pyenv() {
    log_info "Checking pyenv installation..."
    
    # Check if pyenv is installed
    if ! command -v pyenv &> /dev/null; then
        log_error "pyenv is not installed. Please install it first:"
        log_error "brew install pyenv"
        log_error "Then add the following to your ~/.zshrc:"
        log_error 'export PYENV_ROOT="$HOME/.pyenv"'
        log_error 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"'
        log_error 'eval "$(pyenv init -)"'
        return 1
    fi
    
    # Initialize pyenv
    eval "$(pyenv init -)"
    
    # Define target Python version
    local target_version="3.11.7"
    
    # Check if target version is installed
    if ! pyenv versions --bare | grep -q "^${target_version}$"; then
        log_info "Python ${target_version} not found, installing..."
        if ! pyenv install ${target_version}; then
            log_error "Failed to install Python ${target_version}"
            return 1
        fi
    else
        log_info "Python ${target_version} is already installed"
    fi
    
    # Set local Python version for project
    log_info "Setting local Python version to ${target_version}..."
    if ! pyenv local ${target_version}; then
        log_error "Failed to set local Python version"
        return 1
    fi
    
    # Rehash pyenv
    pyenv rehash
    
    # Verify Python version
    local current_version
    current_version=$(python -V 2>&1 | cut -d' ' -f2)
    if [ "$current_version" != "$target_version" ]; then
        log_error "Python version mismatch: expected ${target_version}, got ${current_version}"
        return 1
    fi
    
    log_info "pyenv setup complete"
    log_info "Current Python versions:"
    pyenv versions
    log_info "Active Python version: $(python -V)"
}

# Check Python installation
check_python() {
    log_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi
    
    local version
    version=$(python3 -V 2>&1 | cut -d' ' -f2)
    log_info "Found Python version: $version"
    
    # Verify minimum version (3.11)
    local major
    local minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 11 ]); then
        log_error "Python 3.11 or higher is required"
        return 1
    fi
    
    # Verify maximum version (< 3.14)
    if [ "$major" -gt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -ge 14 ]); then
        log_error "Python version must be less than 3.14"
        return 1
    fi
}

# Check and setup virtual environment
setup_venv() {
    log_info "Checking virtual environment..."
    
    # Check for existing virtual environments
    local venv_count=0
    for venv_dir in .venv venv env; do
        if [ -d "$venv_dir" ]; then
            ((venv_count++))
            if [ "$venv_dir" != ".venv" ]; then
                log_warning "Found existing virtual environment at: $venv_dir"
                log_warning "Please remove it or use .venv instead"
                return 1
            fi
        fi
    done
    
    # Create .venv if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment in .venv..."
        python3 -m venv .venv
        
        # Activate virtual environment
        source .venv/bin/activate
        
        # Upgrade pip
        python3 -m pip install --upgrade pip
    else
        log_info "Using existing virtual environment in .venv"
        source .venv/bin/activate
    fi
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" != *".venv" ]]; then
        log_error "Failed to activate virtual environment"
        return 1
    fi
    
    log_info "Virtual environment is ready"
}

# Check/install poetry
check_poetry() {
    log_info "Checking Poetry installation..."
    
    if ! command -v poetry &> /dev/null; then
        log_info "Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
    fi
    
    log_info "Found Poetry version: $(poetry --version)"
    
    # Configure poetry to use the virtual environment
    poetry config virtualenvs.in-project true
    poetry config virtualenvs.path ".venv"
}

# Create .env file if missing
create_env_file() {
    log_info "Checking .env file..."
    
    if [ -f .env ]; then
        log_info ".env file already exists"
        return 0
    fi
    
    log_info "Creating .env file..."
    
    # Get absolute path of workspace
    local workspace_dir
    workspace_dir=$(pwd)
    
    cat > .env << EOL
# Nova Environment Configuration

# Base Directories
NOVA_BASE_DIR="$workspace_dir"
NOVA_INPUT_DIR="\${NOVA_BASE_DIR}/_NovaInput"
NOVA_OUTPUT_DIR="\${NOVA_BASE_DIR}/_NovaOutput"
NOVA_PROCESSING_DIR="\${NOVA_BASE_DIR}/_NovaProcessing"
NOVA_TEMP_DIR="\${NOVA_PROCESSING_DIR}/temp"
NOVA_STATE_DIR="\${NOVA_PROCESSING_DIR}/.state"

# Phase Directories
NOVA_PHASE_MARKDOWN_PARSE="\${NOVA_PROCESSING_DIR}/phases/markdown_parse"
NOVA_PHASE_MARKDOWN_CONSOLIDATE="\${NOVA_PROCESSING_DIR}/phases/markdown_consolidate"
NOVA_PHASE_MARKDOWN_AGGREGATE="\${NOVA_PROCESSING_DIR}/phases/markdown_aggregate"
NOVA_PHASE_MARKDOWN_SPLIT="\${NOVA_PROCESSING_DIR}/phases/markdown_split"

# Image Directories
NOVA_ORIGINAL_IMAGES_DIR="\${NOVA_PROCESSING_DIR}/images/original"
NOVA_PROCESSED_IMAGES_DIR="\${NOVA_PROCESSING_DIR}/images/processed"
NOVA_IMAGE_METADATA_DIR="\${NOVA_PROCESSING_DIR}/images/metadata"
NOVA_IMAGE_CACHE_DIR="\${NOVA_PROCESSING_DIR}/images/cache"

# Office Directories
NOVA_OFFICE_ASSETS_DIR="\${NOVA_PROCESSING_DIR}/office/assets"
NOVA_OFFICE_TEMP_DIR="\${NOVA_PROCESSING_DIR}/office/temp"

# OpenAI Configuration
OPENAI_API_KEY=""
EOL

    chmod 600 .env
    log_info ".env file created with default values"
    log_info "Please update OPENAI_API_KEY in .env file"
}

# Set up directory structure
setup_directories() {
    log_info "Setting up directory structure..."
    
    # Source environment variables
    if [ -f .env ]; then
        source .env
    else
        log_error ".env file not found"
        return 1
    fi
    
    # Create directories using cleanup script
    ./cleanup.sh create
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Install Python dependencies
    poetry install
    
    # Install development tools
    log_info "Installing development tools..."
    python3 -m pip install pre-commit pytest pytest-cov pytest-mock pytest-asyncio
    
    # Install pre-commit hooks
    log_info "Installing pre-commit hooks..."
    python3 -m pre_commit install
    
    # Verify pytest installation
    if ! python3 -m pytest --version > /dev/null 2>&1; then
        log_error "Failed to install pytest"
        return 1
    fi
    
    log_info "Development tools installed successfully"
}

# Main installation
main() {
    log_info "Starting Nova installation..."
    
    # Check requirements
    setup_pyenv || exit 1
    check_python || exit 1
    setup_venv || exit 1
    check_poetry || exit 1
    
    # Create configuration
    create_env_file
    
    # Set up directories
    setup_directories
    
    # Install dependencies
    install_dependencies
    
    log_info "Installation completed successfully!"
    log_info "Please update OPENAI_API_KEY in .env file before running Nova"
    log_info "Virtual environment is active at .venv"
}

# Execute main function
main