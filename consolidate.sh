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
    echo "\"${path/#$HOME/~}\""
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
    local title="$1"
    python3 -c '
from colors import NovaConsole
console = NovaConsole()
console.section('"\"$title\""')
'
}

# Function to print success
print_success() {
    python -c "
    from colors import NovaConsole
    from src.utils.path_utils import normalize_path
    console = NovaConsole()
    console.success('$1')
    "
}

# Function to print error
print_error() {
    python -c "from colors import NovaConsole; console = NovaConsole(); console.error('$1')"
}

# Function to print info
print_info() {
    python -c "from colors import NovaConsole; console = NovaConsole(); console.info('$1')"
}

# Function to print configuration
print_config() {
    python3 -c "
from rich import print
from src.utils.path_utils import format_path

print('[cyan]Current Configuration:[/]')
print('  Input Directory:      ', end='')
print(format_path('$NOVA_INPUT_DIR'))
print('  Consolidated Output:  ', end='')
print(format_path('$NOVA_CONSOLIDATED_DIR'))
print('  PDF Output:          ', end='')
print(format_path('$NOVA_OUTPUT_DIR'))
print('  Media Directory:     ', end='')
print(format_path('$MEDIA_DIR'))
print()
      "
}

# Function to check Python installation and dependencies
check_python() {
    if ! command -v python &> /dev/null; then
        python -c "from rich import print; print('[red]✗ Error:[/] Python is not installed or not in PATH')"
        exit 1
    fi

    # Check if requirements.txt exists
    if [[ ! -f requirements.txt ]]; then
        python -c "from rich import print; print('[red]✗ Error:[/] requirements.txt not found')"
        exit 1
    fi

    # Check for virtual environment
    if [[ ! -d "venv" ]]; then
        python -c "from rich import print; print('[yellow]⚠ Creating virtual environment...[/]')"
        python -m venv venv
    fi

    # Activate virtual environment and install dependencies
    source venv/bin/activate
    python -c "from rich import print; print('[cyan]Installing dependencies...[/]')"
    pip install -r requirements.txt >/dev/null 2>&1 || {
        python -c "from rich import print; print('[red]✗ Error:[/] Failed to install dependencies')"
        exit 1
    }
}

# Function to check required scripts
check_scripts() {
    local scripts=("markdown_consolidator.py" "markdown_to_pdf_converter.py" "src/processors/pdf_to_markdown_converter.py")
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
    for dir in "$NOVA_INPUT_DIR" "$NOVA_CONSOLIDATED_DIR" "$NOVA_OUTPUT_DIR" "src/utils" "src/processors"; do
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
    python3 -c "
from rich import print
from src.utils.path_utils import format_path

print('[cyan]Removing:[/]')
print('  - ', end='')
print(format_path('$CONSOLIDATED_MD'))
print('  - ', end='')
print(format_path('$MEDIA_DIR'))
print('  - ', end='')
print(format_path('$FINAL_PDF'))
      "
    rm -f "$CONSOLIDATED_MD"
    rm -rf "$MEDIA_DIR"
    rm -f "$FINAL_PDF"
    
    python -c "from rich import print; print('[green]✓[/] Cleanup complete\n')"
}

# Function to run markdown consolidation
consolidate_markdown() {
    print_header "Starting Markdown Consolidation"
    python3 -c "
from rich import print
from src.utils.path_utils import format_path

print('[cyan]Processing files from:[/] ', end='')
print(format_path('$NOVA_INPUT_DIR'))
print('[cyan]Output will be saved to:[/] ', end='')
print(format_path('$CONSOLIDATED_MD'))
      "
      
    mkdir -p "$(dirname "$CONSOLIDATED_MD")"
    mkdir -p "$(dirname "$CONSOLIDATED_MD")/_media"
    
    # Run Python script
    python markdown_consolidator.py "$NOVA_INPUT_DIR" "$CONSOLIDATED_MD"
    CONSOLIDATE_STATUS=$?
    
    if [[ $CONSOLIDATE_STATUS -eq 0 ]] && [[ -f "$CONSOLIDATED_MD" ]] && [[ -s "$CONSOLIDATED_MD" ]]; then
        python3 -c "
from rich import print
from src.utils.path_utils import format_path, get_file_size

print('[green]✓[/] Markdown consolidated successfully')
print('  Location: ', end='')
print(format_path('$CONSOLIDATED_MD'), end='')
print(f' ({get_file_size('$CONSOLIDATED_MD')})')
"
        return 0
    else
        python3 -c "from rich import print; print('[red]✗[/] Markdown consolidation failed')"
        return 1
    fi
}

# Function to convert to PDF
convert_to_pdf() {
    print_header "Converting to PDF"
    python3 -c "
from rich import print
from src.utils.path_utils import format_path

print('[cyan]Input file:[/]  ', end='')
print(format_path('$CONSOLIDATED_MD'))
print('[cyan]Output file:[/] ', end='')
print(format_path('$FINAL_PDF'))
      "
      
    if ! python markdown_to_pdf_converter.py "$CONSOLIDATED_MD" "$FINAL_PDF"; then
        python3 -c "from rich import print; print('[red]✗[/] PDF conversion failed')"
        return 1
    fi
    
    if [[ -f "$FINAL_PDF" ]] && [[ -s "$FINAL_PDF" ]]; then
        python3 -c "
from rich import print
from src.utils.path_utils import format_path, get_file_size

print('[green]✓[/] PDF generated successfully')
print('  Location: ', end='')
print(format_path('$FINAL_PDF'), end='')
print(f' ({get_file_size('$FINAL_PDF')})')
"
        return 0
    else
        python3 -c "from rich import print; print('[red]✗[/] PDF generation failed')"
        return 1
    fi
}

# Function to convert PDFs to markdown
convert_pdfs_to_markdown() {
    print_header "Converting PDF files to Markdown"
    
    # First, find all markdown files that might have associated PDFs
    while IFS= read -r -d '' md_file; do
        # Get the base directory and filename without extension
        base_dir=$(dirname "$md_file")
        base_name=$(basename "$md_file" .md)
        attachment_dir="$base_dir/$base_name"
        
        # Check if there's a matching directory with PDFs
        if [ -d "$attachment_dir" ]; then
            python3 -c "
from colors import NovaConsole
console = NovaConsole()
console.process_start('Processing attachments', '$md_file')
            "
            
            # Process each PDF in the attachment directory
            while IFS= read -r -d '' pdf_file; do
                pdf_name=$(basename "$pdf_file" .pdf)
                md_output="$attachment_dir/$pdf_name.md"
                
                python3 -c "
from colors import NovaConsole
console = NovaConsole()
console.process_item('$pdf_file')
                "
                
                if ! python pdf_to_markdown_converter.py "$pdf_file" "$md_output" --media-dir "$attachment_dir/_media"; then
                    python3 -c "
from colors import NovaConsole
console = NovaConsole()
console.error('PDF conversion failed', '$pdf_file')
                    "
                    return 1
                fi
            done < <(find "$attachment_dir" -maxdepth 1 -name "*.pdf" -print0)
        fi
    done < <(find "$NOVA_INPUT_DIR" -type f -name "*.md" -print0)
    
    python3 -c "
from colors import NovaConsole
console = NovaConsole()
console.process_complete('PDF conversion')
    "
    return 0
}

# Function to ensure we're in a virtual environment
ensure_venv() {
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        if [[ -f "venv/bin/activate" ]]; then
            source venv/bin/activate
        else
            python -c "from rich import print; print('[yellow]⚠ Creating virtual environment...[/]')"
            python -m venv venv
            source venv/bin/activate
        fi
    fi
}

# Main execution
main() {
    timer_start=$(date +%s.%N)
    
    ensure_venv
    print_header "Nova Markdown Processing"
    print_config
    
    check_python
    check_scripts
    check_directories
    
    # Create all required directories first
    for dir in "$(dirname "$CONSOLIDATED_MD")" "$(dirname "$FINAL_PDF")" "$MEDIA_DIR"; do
        mkdir -p "$dir"
    done
    
    cleanup_previous
    
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
    
    timer_end=$(date +%s.%N)
    duration=$(echo "$timer_end - $timer_start" | bc)
    
    print_header "Process Complete"
    python3 -c "
from rich import print
from src.utils.path_utils import format_path, get_file_size
from src.utils.timing import format_duration

print('[cyan]Output Files:[/]')
print('  Markdown: ', end='')
print(format_path('$CONSOLIDATED_MD'), end='')
print(f' ({get_file_size('$CONSOLIDATED_MD')})')
print('  PDF:      ', end='')
print(format_path('$FINAL_PDF'), end='')
print(f' ({get_file_size('$FINAL_PDF')})')
print(f'\n[cyan]Total processing time:[/] {format_duration(float('$duration'))}')
    "
}

# Execute main function
main