#!/bin/bash

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    local message=$1
    echo -e "\n${BOLD}${CYAN}=== ${message} ===${NC}\n"
}

# Function to print step headers
print_step() {
    local step=$1
    local message=$2
    echo -e "\n${CYAN}Step ${step}: ${message}${NC}"
}

# Function to wrap noisy tool output
wrap_noisy_output() {
    local cmd="$1"
    echo -e "${BLUE}┌─────────── Tool Noise (Safe to Ignore) ───────────┐${NC}"
    eval "$cmd"
    echo -e "${BLUE}└──────────────── End Tool Noise ────────────────┘${NC}"
}

# Print banner
echo -e "\n${BOLD}${GREEN}"
echo "███    ██  ██████  ██    ██  █████"
echo "████   ██ ██    ██ ██    ██ ██   ██"
echo "██ ██  ██ ██    ██ ██    ██ ███████"
echo "██  ██ ██ ██    ██  ██  ██  ██   ██"
echo "██   ████  ██████    ████   ██   ██"
echo -e "${NC}"

print_header "Markdown Consolidation and PDF Generation"

# Environment Setup
print_step "1" "Environment Setup"

# Check Poetry installation
print_status "$CYAN" "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    print_status "$YELLOW" "❌ Poetry not found. Please install poetry first."
    exit 1
fi
print_status "$GREEN" "✓ Poetry is installed"

# Load environment variables
print_status "$CYAN" "Loading environment configuration..."
if [ -f .env ]; then
    source .env
    print_status "$GREEN" "✓ Environment configuration loaded"
else
    print_status "$YELLOW" "❌ No .env file found. Please copy .env.template to .env and configure it."
    exit 1
fi

# Directory Setup
print_step "2" "Directory Setup"
print_status "$CYAN" "Creating required directories..."
print_status "$NC" "  Input Dir:  ${NOVA_INPUT_DIR}"
print_status "$NC" "  Output Dir: ${NOVA_OUTPUT_DIR}"
print_status "$NC" "  Debug Dir:  ${NOVA_DEBUG_DIR}"
print_status "$NC" "  HTML Dir:   ${NOVA_DEBUG_DIR}/html"

mkdir -p "${NOVA_INPUT_DIR}" "${NOVA_CONSOLIDATED_DIR}" "${NOVA_OUTPUT_DIR}" "${NOVA_DEBUG_DIR}/html"
print_status "$GREEN" "✓ Directories created/verified"

# Markdown Consolidation
print_step "3" "Markdown Consolidation"
print_status "$CYAN" "Consolidating markdown files..."
print_status "$NC" "Source: ${NOVA_INPUT_DIR}"
print_status "$NC" "Target: ${NOVA_CONSOLIDATED_DIR}/consolidated.md"
print_status "$NC" "HTML Files: ${NOVA_DEBUG_DIR}/html/*.html"

# Run consolidation with debug output
print_status "$CYAN" "\nProcessing files..."
echo
poetry run python -m src.cli process --force --debug-dir "${NOVA_DEBUG_DIR}" "$@"
echo

# Show HTML files if they exist
if [ -d "${NOVA_DEBUG_DIR}/html" ]; then
    html_count=$(ls -1 "${NOVA_DEBUG_DIR}/html"/*.html 2>/dev/null | wc -l)
    if [ $html_count -gt 0 ]; then
        print_status "$GREEN" "✓ Generated HTML files:"
        echo
        for html_file in "${NOVA_DEBUG_DIR}/html"/*.html; do
            print_status "$CYAN" "  📄 $(basename "$html_file")"
        done
        echo
    fi
fi

# Show consolidated files if they exist
if [ -f "${NOVA_CONSOLIDATED_DIR}/consolidated.md" ]; then
    print_status "$GREEN" "✓ Generated consolidated markdown:"
    print_status "$CYAN" "  📄 consolidated.md"
    echo
fi

if [ -f "${NOVA_CONSOLIDATED_DIR}/consolidated.html" ]; then
    print_status "$GREEN" "✓ Generated consolidated HTML:"
    print_status "$CYAN" "  📄 consolidated.html"
    echo
fi

if [ -f "${NOVA_CONSOLIDATED_DIR}/final.pdf" ]; then
    print_status "$GREEN" "✓ Generated PDF:"
    print_status "$CYAN" "  📄 final.pdf"
    echo
fi

# Final Status
if [ $? -eq 0 ]; then
    print_header "Process Complete"
    print_status "$GREEN" "✓ All steps completed successfully"
    echo
    print_status "$GREEN" "Generated Files:"
    print_status "$CYAN" "  📄 HTML Files:         ${NOVA_DEBUG_DIR}/html/"
    print_status "$CYAN" "  📄 Consolidated Files: ${NOVA_CONSOLIDATED_DIR}/"
    print_status "$CYAN" "  📄 Debug Structure:"
    print_status "$NC" "    html/          (HTML output files)"
    print_status "$NC" "    attachments/   (Documents, PDFs, etc.)"
    print_status "$NC" "    media/         (Images and other media)"
    echo
    print_status "$CYAN" "View the files above to see the results"
else
    print_header "Process Failed"
    print_status "$YELLOW" "❌ Processing failed. Check the logs for details."
    exit 1
fi
