#!/bin/bash

# Set up colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
INPUT_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/_NovaIndividualMarkdown"
CONSOLIDATED_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/_NovaConsolidatedMarkdown"
PDF_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/_Nova"
DEBUG_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/_NovaDebug"
MEDIA_DIR="$CONSOLIDATED_DIR/_media"
TEMPLATE_DIR="src/resources/templates/default.html"

# Print section header
print_section() {
    printf "\n\n%s\n\n" "$(printf '%.s─' {1..100})"
    printf "%s%*s%s\n\n" "$(printf '%.s─' {1..35})" $((30)) "$1" "$(printf '%.s─' {1..35})"
}

# Print configuration
print_section "Nova Markdown Processing"
echo "Current Configuration:"
echo "  Input Directory:      $INPUT_DIR"
echo "  Consolidated Output:  $CONSOLIDATED_DIR"
echo "  PDF Output:          $PDF_DIR"
echo "  Debug Output:        $DEBUG_DIR"
echo "  Media Directory:     $MEDIA_DIR"
echo "  Template Directory:  $TEMPLATE_DIR"

# Check directories
echo -e "\nChecking directories..."
for dir in "$INPUT_DIR" "$CONSOLIDATED_DIR" "$PDF_DIR" "$MEDIA_DIR" "$DEBUG_DIR"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
done
echo -e "${GREEN}✓${NC} Directory check complete"

# Clean up previous files
print_section "Cleaning up previous files"
echo "Removing:"
echo "  - $CONSOLIDATED_DIR/output.md"
echo "  - $CONSOLIDATED_DIR/_media"
echo "  - $PDF_DIR/output.pdf"
echo "  - $DEBUG_DIR/*.html"

rm -f "$CONSOLIDATED_DIR/output.md"
rm -rf "$CONSOLIDATED_DIR/_media"
rm -f "$PDF_DIR/output.pdf"
rm -f "$DEBUG_DIR"/*.html

echo -e "${GREEN}✓${NC} Cleanup complete"

# Convert PDF files to markdown
print_section "Converting PDF files to Markdown"

# Run the Python script
poetry run python -c "
from pathlib import Path
from src.core.markdown_consolidator import consolidate
from src.core.markdown_to_pdf_converter import convert_markdown_to_pdf

# Consolidate markdown files
consolidate(
    input_path=Path('$INPUT_DIR'),
    output_file=Path('$CONSOLIDATED_DIR/output.md'),
    recursive=True,
    verbose=True
)

# Convert to PDF
convert_markdown_to_pdf(
    input_file='$CONSOLIDATED_DIR/output.md',
    output_file='$PDF_DIR/output.pdf',
    media_dir='$CONSOLIDATED_DIR/_media',
    template_dir='$TEMPLATE_DIR',
    debug_dir='$DEBUG_DIR'
)"
