#!/bin/zsh

# nova-process.sh
# Script to process Nova markdown files and generate consolidated output
# Created: November 2024

# Set strict error handling
set -e  # Exit on error
set -u  # Exit on undefined variable

# Define base paths to make the script more maintainable
ICLOUD_BASE="/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs"
NOVA_INPUT_DIR="$ICLOUD_BASE/_NovaIndividualMarkdown"
NOVA_CONSOLIDATED_DIR="$ICLOUD_BASE/_NovaConsolidatedMarkdown"
NOVA_OUTPUT_DIR="$ICLOUD_BASE/_Nova"

# Define output files
CONSOLIDATED_MD="$NOVA_CONSOLIDATED_DIR/output.md"
MEDIA_DIR="$NOVA_CONSOLIDATED_DIR/_media"
FINAL_PDF="$NOVA_OUTPUT_DIR/output.pdf"

# Function to check if Python is installed
check_python() {
    if ! command -v python &> /dev/null; then
        echo "Error: Python is not installed or not in PATH"
        exit 1
    fi
}

# Function to check if required Python scripts exist
check_scripts() {
    local scripts=("markdown_consolidator.py" "markdown_to_pdf_converter.py")
    for script in $scripts; do
        if [[ ! -f $script ]]; then
            echo "Error: Required Python script '$script' not found in current directory"
            exit 1
        fi
    done
}

# Function to clean up previous output files
cleanup_previous() {
    echo "Cleaning up previous output files..."
    rm -f "$CONSOLIDATED_MD"
    rm -rf "$MEDIA_DIR"
    rm -f "$FINAL_PDF"
}

# Function to run the markdown consolidation
consolidate_markdown() {
    echo "Consolidating markdown files..."
    python markdown_consolidator.py "$NOVA_INPUT_DIR" "$CONSOLIDATED_MD"
}

# Function to convert to PDF
convert_to_pdf() {
    echo "Converting to PDF..."
    python markdown_to_pdf_converter.py "$CONSOLIDATED_MD" "$FINAL_PDF"
}

# Main execution
main() {
    echo "Starting Nova markdown processing..."
    
    # Run pre-flight checks
    check_python
    check_scripts
    
    # Execute the processing steps
    cleanup_previous
    consolidate_markdown
    convert_to_pdf
    
    echo "Processing complete!"
    echo "Output files:"
    echo "  Markdown: $CONSOLIDATED_MD"
    echo "  PDF: $FINAL_PDF"
}

# Execute main function
main