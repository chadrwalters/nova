#!/bin/zsh

# nova-process.sh
# Script to process Nova markdown files and generate consolidated output
# Created: November 2024

# Set strict error handling
set -e  # Exit on error
set -u  # Exit on undefined variable

# Function to print status messages with color
print_status() {
    echo "\033[1;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
    echo "\033[1;34m$1\033[0m"
    echo "\033[1;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
}

# Function to print success messages
print_success() {
    echo "\033[1;32m✓ $1\033[0m"
}

# Function to print error messages
print_error() {
    echo "\033[1;31m✗ $1\033[0m"
}

# Function to print warning messages
print_warning() {
    echo "\033[1;33m⚠️  $1\033[0m"
}

# Function to print info messages
print_info() {
    echo "\033[1;36m$1\033[0m"
}

# Function to clean path (remove trailing slashes and normalize)
clean_path() {
    local path="$1"
    # Remove trailing slash and escaped spaces
    path="${path%/}"
    path="${path//\\ / }"
    echo "$path"
}

# Load environment variables
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please copy .env.template to .env and update the values"
    exit 1
fi

source .env

# Clean and normalize paths
NOVA_INPUT_DIR=$(clean_path "$NOVA_INPUT_DIR")
NOVA_CONSOLIDATED_DIR=$(clean_path "$NOVA_CONSOLIDATED_DIR")
NOVA_OUTPUT_DIR=$(clean_path "$NOVA_OUTPUT_DIR")

# Define output files (using clean paths)
CONSOLIDATED_MD="$NOVA_CONSOLIDATED_DIR/output.md"
MEDIA_DIR="$NOVA_CONSOLIDATED_DIR/_media"
FINAL_PDF="$NOVA_OUTPUT_DIR/output.pdf"

# Function to normalize path display
normalize_path() {
    local path="$1"
    # Remove any escaped spaces and convert to ~
    path="${path//\\ / }"  # Remove escaped spaces
    echo "${path/#$HOME/~}"
}

# Function to print variable values
print_vars() {
    print_info "Current Configuration:"
    echo "  Input Directory:      $(normalize_path "$NOVA_INPUT_DIR")"
    echo "  Consolidated Output:  $(normalize_path "$NOVA_CONSOLIDATED_DIR")"
    echo "  PDF Output:          $(normalize_path "$NOVA_OUTPUT_DIR")"
    echo "  Media Directory:     $(normalize_path "$MEDIA_DIR")"
    echo
}

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

# Function to check directories
check_directories() {
    print_info "Checking directories..."
    for dir in "$NOVA_INPUT_DIR" "$NOVA_CONSOLIDATED_DIR" "$NOVA_OUTPUT_DIR"; do
        if [[ ! -d "$dir" ]]; then
            print_info "Creating directory: $(normalize_path "$dir")"
            mkdir -p "$dir"
        fi
    done
    print_success "Directory check complete"
    echo
}

# Function to clean up previous output files
cleanup_previous() {
    print_status "Cleaning up previous files"
    print_info "Removing:"
    echo "  - $(normalize_path "$CONSOLIDATED_MD")"
    echo "  - $(normalize_path "$MEDIA_DIR")"
    echo "  - $(normalize_path "$FINAL_PDF")"
    
    rm -f "$CONSOLIDATED_MD"
    rm -rf "$MEDIA_DIR"
    rm -f "$FINAL_PDF"
    
    print_success "Cleanup complete"
    echo
}

# Function to wait for file to appear
wait_for_file() {
    local file="$1"
    local display_path="$(normalize_path "$file")"
    local timeout=60
    local counter=0
    
    print_info "Waiting for file to appear: $display_path"
    while [ $counter -lt $timeout ]; do
        if [[ -f "$file" ]]; then
            if [[ -s "$file" ]]; then
                print_success "File found and has content after $counter seconds"
                return 0
            fi
        fi
        
        if ls -la "$file" 2>/dev/null | grep -q "com.apple.icloud"; then
            print_warning "File exists in iCloud but is still syncing..."
            sleep 5
            continue
        fi
        
        sleep 1
        counter=$((counter + 1))
        echo -n "."
    done
    
    if grep -q "Successfully wrote consolidated file to.*output.md" markdown_consolidator.log; then
        print_warning "File reported as written but not immediately visible"
        print_info "This is normal with iCloud Drive. Continuing..."
        return 0
    fi
    
    print_error "Timeout waiting for file"
    return 1
}

# Function to run the markdown consolidation
consolidate_markdown() {
    print_status "Starting Markdown Consolidation"
    print_info "Processing files from: $(normalize_path "$NOVA_INPUT_DIR")"
    print_info "Output will be saved to: $(normalize_path "$CONSOLIDATED_MD")"
    
    mkdir -p "$(dirname "$CONSOLIDATED_MD")"
    mkdir -p "$(dirname "$CONSOLIDATED_MD")/_media"
    
    # Clean up paths for Python script
    INPUT_PATH="${NOVA_INPUT_DIR//\\ / }"
    OUTPUT_PATH="${CONSOLIDATED_MD//\\ / }"
    
    # Run the Python script and capture its exit status
    python markdown_consolidator.py "$INPUT_PATH" "$OUTPUT_PATH"
    CONSOLIDATE_STATUS=$?
    
    if [[ $CONSOLIDATE_STATUS -eq 0 ]]; then
        sleep 5
        
        if wait_for_file "$CONSOLIDATED_MD"; then
            print_success "Markdown consolidated successfully"
            print_info "  Location: $(normalize_path "$CONSOLIDATED_MD")"
            if [[ -f "$CONSOLIDATED_MD" ]]; then
                print_info "  Size: $(ls -lh "$CONSOLIDATED_MD" 2>/dev/null | awk '{print $5}' || echo "unknown")"
            else
                print_info "  Size: unknown (file still syncing)"
            fi
            
            if [[ ! -f "$CONSOLIDATED_MD" ]]; then
                print_warning "Waiting for iCloud to complete sync..."
                sleep 10
            fi
            
            return 0
        fi
    fi
    
    if [[ -f "markdown_consolidator.log" ]]; then
        print_error "Consolidation failed. Last few lines of log file:"
        tail -n 5 markdown_consolidator.log
    fi
    
    return 1
}

# Function to convert to PDF
convert_to_pdf() {
    if [[ ! -f "$CONSOLIDATED_MD" ]]; then
        print_info "Waiting for markdown file to sync..."
        sleep 15
    fi

    if [[ ! -f "$CONSOLIDATED_MD" ]] || [[ ! -s "$CONSOLIDATED_MD" ]]; then
        print_error "Cannot convert to PDF: Markdown file is missing or empty"
        print_info "  Looking for: $(normalize_path "$CONSOLIDATED_MD")"
        return 1
    fi

    print_status "Converting to PDF"
    print_info "Input file:  $(normalize_path "$CONSOLIDATED_MD")"
    print_info "Output file: $(normalize_path "$FINAL_PDF")"
    echo
    
    if ! python markdown_to_pdf_converter.py "$CONSOLIDATED_MD" "$FINAL_PDF"; then
        print_error "PDF conversion failed"
        return 1
    fi

    if [ ! -f "$FINAL_PDF" ]; then
        print_error "PDF file was not created"
        return 1
    fi

    if [ ! -s "$FINAL_PDF" ]; then
        print_error "PDF file is empty"
        return 1
    fi

    print_success "PDF generated successfully"
    print_info "  Location: $(normalize_path "$FINAL_PDF")"
    print_info "  Size: $(du -h "$FINAL_PDF" | cut -f1)"
    echo
    return 0
}

# Main execution
main() {
    print_status "Starting Nova markdown processing"
    print_vars
    
    check_python
    check_scripts
    check_directories
    
    cleanup_previous
    if ! consolidate_markdown; then
        print_error "Markdown consolidation failed"
        exit 1
    fi
    
    if ! convert_to_pdf; then
        print_error "PDF conversion failed"
        exit 1
    fi
    
    print_status "Process Complete"
    print_info "Output Files:"
    echo "  Markdown: $(normalize_path "$CONSOLIDATED_MD") ($(du -h "$CONSOLIDATED_MD" | cut -f1))"
    echo "  PDF:      $(normalize_path "$FINAL_PDF") ($(du -h "$FINAL_PDF" | cut -f1))"
}

# Execute main function
main