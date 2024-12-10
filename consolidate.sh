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
echo "  Processing Dir:    ${NOVA_PROCESSING_DIR}"

# Create required directories with proper permissions
umask 0022  # Set default permissions to 755 for directories and 644 for files
mkdir -p "${NOVA_INPUT_DIR}"
mkdir -p "${NOVA_OUTPUT_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}"

# Create processing subdirectories
mkdir -p "${NOVA_PROCESSING_DIR}/html"
mkdir -p "${NOVA_PROCESSING_DIR}/consolidated"
mkdir -p "${NOVA_PROCESSING_DIR}/media"
mkdir -p "${NOVA_PROCESSING_DIR}/attachments"
mkdir -p "${NOVA_PROCESSING_DIR}/temp"

# Ensure write permissions
chmod 755 "${NOVA_INPUT_DIR}" "${NOVA_OUTPUT_DIR}" "${NOVA_PROCESSING_DIR}"
chmod 755 "${NOVA_PROCESSING_DIR}"/{html,consolidated,media,attachments,temp}

echo "✓ Directories created/verified"

# Step 3: Markdown Consolidation and PDF Generation
echo -e "\nStep 3: Markdown Consolidation and PDF Generation"
echo "Processing files..."
echo "Source: ${NOVA_INPUT_DIR}"
echo "Target: ${NOVA_OUTPUT_DIR}/consolidated.pdf"

# Install dependencies
echo "Installing dependencies..."
poetry install

poetry run python -m src.cli.main consolidate \
    --input-dir "${NOVA_INPUT_DIR}" \
    --output-dir "${NOVA_OUTPUT_DIR}" \
    --processing-dir "${NOVA_PROCESSING_DIR}" \
    --template-dir "src/resources/templates"

# Print completion message
echo -e "\n=== Process Complete ==="
echo -e "\n✓ All steps completed successfully"

# Print generated files
echo -e "\nGenerated Files:"
echo "  📄 Input Files:        ${NOVA_INPUT_DIR}/"
echo "  📄 Output Files:       ${NOVA_OUTPUT_DIR}/"
echo "  📄 Processing Files:   ${NOVA_PROCESSING_DIR}/"

echo -e "\nDirectory Structure:"
echo "    input/         (Source markdown files)"
echo "    output/        (Final PDF output)"
echo "    processing/    (Processing files)"

echo -e "\nView the files above to see the results"
