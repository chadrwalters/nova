#!/bin/bash

# Script to set environment variables for Nova

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

# Check if .env file exists
if [ ! -f ".env" ]; then
    log_info "Creating .env file..."
    cat > .env << EOF
# Nova Environment Variables
OPENAI_API_KEY=your_openai_api_key_here
EOF
    log_success "Created .env file"
    log_warning "Please edit .env file and add your OpenAI API key"
    exit 1
fi

# Source the .env file
log_info "Loading environment variables..."
set -a
source .env
set +a
log_success "Environment variables loaded"

# Export variables to current shell
export OPENAI_API_KEY

# Verify API key is set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    log_error "OpenAI API key not set. Please edit .env file"
    exit 1
fi

log_success "API key verified" 