#!/bin/zsh

# nova-process.sh
# Script to process Nova markdown files and generate consolidated output
# Created: November 2024

# Set strict error handling
set -e  # Exit on error
set -u  # Exit on undefined variable

# Function to normalize path display
normalize_path() {
    local path="$1"
    echo "${path/#$HOME/~}"
}

# Function to clean path (remove trailing slashes and normalize)
clean_path() {
    local path="$1"
    path="${path%/}"
    path="${path//\\ / }"
    echo "$path"
}

# Load environment variables
if [ ! -f .env ]; then
    python -c "from rich import print; print('[red]✗ Error:[/] .env file not found\nPlease copy .env.template to .env and update the values')"
    exit 1
fi

source .env

# Clean and normalize paths
NOVA_INPUT_DIR=$(clean_path "$NOVA_INPUT_DIR")
NOVA_CONSOLIDATED_DIR=$(clean_path "$NOVA_CONSOLIDATED_DIR")
NOVA_OUTPUT_DIR=$(clean_path "$NOVA_OUTPUT_DIR")

# Define output files
CONSOLIDATED_MD="$NOVA_CONSOLIDATED_DIR/output.md"
MEDIA_DIR="$NOVA_CONSOLIDATED_DIR/_media"
FINAL_PDF="$NOVA_OUTPUT_DIR/output.pdf"

# Function to print status header
print_header() {
    python -c "from colors import Colors; Colors.divider(); Colors.header('$1'); Colors.divider()"
}

# Function to print success
print_success() {
    python -c "from colors import Colors; Colors.success('$1')"
}

# Function to print error
print_error() {
    python -c "from colors import Colors; Colors.error('$1')"
}

# Function to print info
print_info() {
    python -c "from colors import Colors; Colors.info('$1')"
}

# Function to print configuration
print_config() {
    python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print('[cyan]Current Configuration:[/]')
print(f'  Input Directory:      {normalize_path('$NOVA_INPUT_DIR')}')
print(f'  Consolidated Output:  {normalize_path('$NOVA_CONSOLIDATED_DIR')}')
print(f'  PDF Output:          {normalize_path('$NOVA_OUTPUT_DIR')}')
print(f'  Media Directory:     {normalize_path('$MEDIA_DIR')}')
print()
"
}

# Function to check Python installation
check_python() {
    if ! command -v python &> /dev/null; then
        python -c "from rich import print; print('[red]✗ Error:[/] Python is not installed or not in PATH')"
        exit 1
    fi
}

# Function to check required scripts
check_scripts() {
    local scripts=("markdown_consolidator.py" "markdown_to_pdf_converter.py" "pdf_to_markdown_converter.py")
    for script in $scripts; do
        if [[ ! -f $script ]]; then
            python -c "from rich import print; print(f'[red]✗ Error:[/] Required Python script \"$script\" not found')"
            exit 1
        fi
    done
}

# Function to check directories
check_directories() {
    python -c "from rich import print; print('[cyan]Checking directories...[/]')"
    for dir in "$NOVA_INPUT_DIR" "$NOVA_CONSOLIDATED_DIR" "$NOVA_OUTPUT_DIR"; do
        if [[ ! -d "$dir" ]]; then
            python -c "from rich import print; print(f'[cyan]Creating directory: {normalize_path('$dir')}[/]')"
            mkdir -p "$dir"
        fi
    done
    python -c "from rich import print; print('[green]✓[/] Directory check complete\n')"
}

# Function to clean up previous files
cleanup_previous() {
    print_header "Cleaning up previous files"
    python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print('[cyan]Removing:[/]')
print(f'  - {normalize_path('$CONSOLIDATED_MD')}')
print(f'  - {normalize_path('$MEDIA_DIR')}')
print(f'  - {normalize_path('$FINAL_PDF')}')
"
    rm -f "$CONSOLIDATED_MD"
    rm -rf "$MEDIA_DIR"
    rm -f "$FINAL_PDF"
    
    python -c "from rich import print; print('[green]✓[/] Cleanup complete\n')"
}

# Function to run markdown consolidation
consolidate_markdown() {
    print_header "Starting Markdown Consolidation"
    python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print(f'[cyan]Processing files from:[/] {normalize_path('$NOVA_INPUT_DIR')}')
print(f'[cyan]Output will be saved to:[/] {normalize_path('$CONSOLIDATED_MD')}')
"
    
    mkdir -p "$(dirname "$CONSOLIDATED_MD")"
    mkdir -p "$(dirname "$CONSOLIDATED_MD")/_media"
    
    # Run Python script
    python markdown_consolidator.py "$NOVA_INPUT_DIR" "$CONSOLIDATED_MD"
    CONSOLIDATE_STATUS=$?
    
    if [[ $CONSOLIDATE_STATUS -eq 0 ]] && [[ -f "$CONSOLIDATED_MD" ]] && [[ -s "$CONSOLIDATED_MD" ]]; then
        python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print('[green]✓[/] Markdown consolidated successfully')
print(f'  Location: {normalize_path('$CONSOLIDATED_MD')}')
print(f'  Size: $(du -h "$CONSOLIDATED_MD" | cut -f1)')
"
        return 0
    else
        python -c "from rich import print; print('[red]✗[/] Markdown consolidation failed')"
        return 1
    fi
}

# Function to convert to PDF
convert_to_pdf() {
    print_header "Converting to PDF"
    python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print(f'[cyan]Input file:[/]  {normalize_path('$CONSOLIDATED_MD')}')
print(f'[cyan]Output file:[/] {normalize_path('$FINAL_PDF')}')
print()
"
    
    if ! python markdown_to_pdf_converter.py "$CONSOLIDATED_MD" "$FINAL_PDF"; then
        python -c "from rich import print; print('[red]✗[/] PDF conversion failed')"
        return 1
    fi

    if [[ -f "$FINAL_PDF" ]] && [[ -s "$FINAL_PDF" ]]; then
        python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print('[green]✓[/] PDF generated successfully')
print(f'  Location: {normalize_path('$FINAL_PDF')}')
print(f'  Size: $(du -h "$FINAL_PDF" | cut -f1)')
print()
"
        return 0
    else
        python -c "from rich import print; print('[red]✗[/] PDF generation failed')"
        return 1
    fi
}

# Function to convert PDF files to markdown
convert_pdfs_to_markdown() {
    print_header "Converting PDF files to Markdown"
    
    # Use find with print0 and process with while read to handle spaces correctly
    local count=0
    while IFS= read -r -d '' pdf_file; do
        ((count++))
    done < <(find "$NOVA_INPUT_DIR" -name "*.pdf" -print0)
    
    if [ $count -eq 0 ]; then
        print_info "No PDF files found to convert"
        return 0
    fi
    
    print_info "Found $count PDF files to convert"
    
    # Create media directory
    local media_dir="$NOVA_INPUT_DIR/_media"
    mkdir -p "$media_dir"
    
    # Process files
    while IFS= read -r -d '' pdf_file; do
        # Create output path maintaining directory structure
        local rel_path="${pdf_file#$NOVA_INPUT_DIR/}"
        local md_file="$NOVA_INPUT_DIR/${rel_path%.pdf}.md"
        
        # Create directory structure if it doesn't exist
        mkdir -p "$(dirname "$md_file")"
        
        print_info "Converting: $(normalize_path "$pdf_file")"
        
        if ! python pdf_to_markdown_converter.py "$pdf_file" "$md_file" --media-dir "$media_dir"; then
            print_error "Failed to convert PDF: $(normalize_path "$pdf_file")"
            return 1
        fi
    done < <(find "$NOVA_INPUT_DIR" -name "*.pdf" -print0)
    
    print_success "PDF conversion complete"
    return 0
}

# Main execution
main() {
    print_header "Starting Nova markdown processing"
    print_config
    
    check_python
    check_scripts
    check_directories
    
    cleanup_previous
    
    # Add PDF conversion step
    if ! convert_pdfs_to_markdown; then
        print_error "PDF conversion failed"
        exit 1
    fi
    
    if ! consolidate_markdown; then
        print_error "Markdown consolidation failed"
        exit 1
    fi
    
    if ! convert_to_pdf; then
        print_error "PDF conversion failed"
        exit 1
    fi
    
    print_header "Process Complete"
    python -c "
from rich import print
import os

def normalize_path(path):
    return path.replace(os.environ['HOME'], '~')

print('[cyan]Output Files:[/]')
print(f'  Markdown: {normalize_path('$CONSOLIDATED_MD')} ($(du -h "$CONSOLIDATED_MD" | cut -f1))')
print(f'  PDF:      {normalize_path('$FINAL_PDF')} ($(du -h "$FINAL_PDF" | cut -f1))')
"
}

# Execute main function
main