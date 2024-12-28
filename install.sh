#!/bin/bash

# Nova Installation Script
# Sets up the Nova environment and dependencies

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
MIN_PYTHON_VERSION="3.11.7"
REQUIRED_SYSTEM_PACKAGES=(
    "tesseract"
    "libheif"
    "imagemagick"
    "ffmpeg"
)

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

# Version comparison function
version_compare() {
    echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }';
}

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python ${MIN_PYTHON_VERSION} or higher."
        exit 1
    fi

    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    if [ $(version_compare "$python_version") -lt $(version_compare "$MIN_PYTHON_VERSION") ]; then
        log_error "Python ${MIN_PYTHON_VERSION} or higher is required. Found version ${python_version}"
        exit 1
    fi

    log_success "Found Python $python_version"
}

# Check Poetry installation
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        log_info "Poetry not found. Installing..."
        curl -sSL https://install.python-poetry.org | python3 -
    fi

    log_success "Poetry is installed"
}

# Check system dependencies
check_system_dependencies() {
    local missing_packages=()

    # Check for Homebrew on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &> /dev/null; then
            log_error "Homebrew not found. Please install Homebrew first."
            exit 1
        fi
    fi

    # Check each required package
    for package in "${REQUIRED_SYSTEM_PACKAGES[@]}"; do
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if ! brew list "$package" &> /dev/null; then
                missing_packages+=("$package")
            fi
        else
            if ! command -v "$package" &> /dev/null; then
                missing_packages+=("$package")
            fi
        fi
    done

    # Install missing packages
    if [ ${#missing_packages[@]} -ne 0 ]; then
        log_info "Installing missing system packages: ${missing_packages[*]}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install "${missing_packages[@]}"
        else
            sudo apt-get update
            sudo apt-get install -y "${missing_packages[@]}"
        fi
    fi

    log_success "All system dependencies are installed"
}

# Create virtual environment and install dependencies
setup_environment() {
    # Remove existing virtual environment if it exists
    if [ -d "$VENV_DIR" ]; then
        log_info "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    fi

    # Configure Poetry to create virtual environment in project directory
    poetry config virtualenvs.in-project true

    # Install dependencies and package in development mode
    log_info "Installing project dependencies..."
    poetry install --no-root
    poetry install -E all

    log_success "Virtual environment created and dependencies installed"
}

# Create or update config file
setup_config() {
    local config_file="${SCRIPT_DIR}/config/nova.yaml"
    local config_template="${SCRIPT_DIR}/config/nova.template.yaml"

    # Check if config template exists
    if [ ! -f "$config_template" ]; then
        log_error "Configuration template not found at: $config_template"
        exit 1
    fi

    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$config_file")"

    # Create config file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        cp "$config_template" "$config_file"
        log_info "Created configuration file from template"
        log_warning "Please edit config/nova.yaml and add your API keys"
    else
        # Validate configuration
        if ! python3 -c "import yaml; yaml.safe_load(open('$config_file'))"; then
            log_error "Invalid YAML configuration file"
            exit 1
        fi
        log_success "Configuration file is valid"
    fi
}

# Create required directories
setup_directories() {
    local icloud_dir="${HOME}/Library/Mobile Documents/com~apple~CloudDocs"
    local input_dir="${icloud_dir}/_NovaInput"
    local processing_dir="${icloud_dir}/_NovaProcessing"

    # Create _NovaInput directory if it doesn't exist
    if [ ! -d "$input_dir" ]; then
        log_info "Creating _NovaInput directory..."
        mkdir -p "$input_dir"
    fi

    # Create _NovaProcessing directory if it doesn't exist
    if [ ! -d "$processing_dir" ]; then
        log_info "Creating _NovaProcessing directory..."
        mkdir -p "$processing_dir"
    fi

    log_success "Required directories are set up"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."

    # Run a simple test
    if poetry run python3 -c "import nova; print('Nova package found')" &> /dev/null; then
        log_success "Nova package is installed correctly"
    else
        log_error "Nova package installation validation failed"
        exit 1
    fi

    # Validate configuration
    if ! poetry run python3 -c "from nova.config.manager import ConfigManager; ConfigManager()"; then
        log_error "Configuration validation failed"
        exit 1
    fi
    log_success "Configuration is valid"
}

# Main installation process
main() {
    log_info "Starting Nova installation..."

    # Perform checks and setup
    check_python
    check_poetry
    check_system_dependencies
    setup_environment
    setup_config
    setup_directories
    validate_installation

    log_success "Nova installation completed successfully"
    log_info "You can now run './run_nova.sh' to process documents"
}

# Run main installation
main