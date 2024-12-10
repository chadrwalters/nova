#!/bin/bash

# Load environment variables
source .env

# Print banner
echo "


███    ██  ██████  ██    ██  █████
████   ██ ██    ██ ██    ██ ██   ██
██ ██  ██ ██    ██ ██    ██ ███████
██  ██ ██ ██    ██  ██  ██  ██   ██
██   ████  ██████    ████   ██   ██


"

echo "=== Markdown Consolidation and PDF Generation ==="

# Step 1: Environment Setup
echo -e "\nStep 1: Environment Setup"
echo "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first."
    exit 1
fi
echo "✓ Poetry is installed"

echo "Checking wkhtmltopdf installation..."
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "Installing wkhtmltopdf..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install wkhtmltopdf
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y wkhtmltopdf
    else
        echo "❌ Please install wkhtmltopdf manually: https://wkhtmltopdf.org/downloads.html"
        exit 1
    fi
fi
echo "✓ wkhtmltopdf is installed"

echo "Loading environment configuration..."
if [ ! -f .env ]; then
    echo "❌ Environment file not found"
    exit 1
fi
echo "✓ Environment configuration loaded"

# Step 2: Directory Setup
echo -e "\nStep 2: Directory Setup"
echo "Creating required directories..."
echo "  Input Dir:         ${NOVA_INPUT_DIR}"
echo "  Output Dir:        ${NOVA_OUTPUT_DIR}"
echo "  Consolidated Dir:  ${NOVA_CONSOLIDATED_DIR}"
echo "  Processing Dir:    ${NOVA_PROCESSING_DIR}"
echo "  Temp Dir:         ${NOVA_TEMP_DIR}"
echo "  Media Dir:        ${NOVA_MEDIA_DIR}"

# Create required directories
mkdir -p "${NOVA_INPUT_DIR}"
mkdir -p "${NOVA_OUTPUT_DIR}"
mkdir -p "${NOVA_CONSOLIDATED_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}"
mkdir -p "${NOVA_TEMP_DIR}"
mkdir -p "${NOVA_MEDIA_DIR}"

# Create processing subdirectories
mkdir -p "${NOVA_PROCESSING_DIR}/html"
mkdir -p "${NOVA_PROCESSING_DIR}/attachments"

echo "✓ Directories created/verified"

# Step 3: Markdown Consolidation and PDF Generation
echo -e "\nStep 3: Markdown Consolidation and PDF Generation"
echo "Processing files..."
echo "Source: ${NOVA_INPUT_DIR}"
echo "Target: ${NOVA_OUTPUT_DIR}/consolidated.pdf"

poetry run python -m src.cli.main consolidate \
    --input-dir "${NOVA_INPUT_DIR}" \
    --output-dir "${NOVA_OUTPUT_DIR}" \
    --consolidated-dir "${NOVA_CONSOLIDATED_DIR}" \
    --processing-dir "${NOVA_PROCESSING_DIR}" \
    --temp-dir "${NOVA_TEMP_DIR}"

# Print completion message
echo -e "\n=== Process Complete ==="
echo -e "\n✓ All steps completed successfully"

# Print generated files
echo -e "\nGenerated Files:"
echo "  📄 Input Files:        ${NOVA_INPUT_DIR}/"
echo "  📄 Consolidated Files: ${NOVA_CONSOLIDATED_DIR}/"
echo "  📄 Output Files:       ${NOVA_OUTPUT_DIR}/"
echo "  📄 Processing Files:   ${NOVA_PROCESSING_DIR}/"
echo "  📄 Media Files:        ${NOVA_MEDIA_DIR}/"

echo -e "\nDirectory Structure:"
echo "    input/         (Source markdown files)"
echo "    consolidated/  (Consolidated markdown and HTML)"
echo "    output/        (Final PDF output)"
echo "    processing/    (Processing files)"
echo "    media/        (Images and other media)"

echo -e "\nView the files above to see the results"
