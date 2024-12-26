#!/bin/bash

# Source environment variables
source .env 2>/dev/null || true

# Validate environment variables
echo "Validating environment variables..."

# Required directories
NOVA_BASE_DIR="${NOVA_BASE_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs}"
NOVA_INPUT_DIR="${NOVA_INPUT_DIR:-$NOVA_BASE_DIR/_NovaInput}"
NOVA_PROCESSING_DIR="${NOVA_PROCESSING_DIR:-$NOVA_BASE_DIR/_NovaProcessing}"
NOVA_PHASE_MARKDOWN_PARSE="${NOVA_PHASE_MARKDOWN_PARSE:-$NOVA_PROCESSING_DIR/phases/markdown_parse}"

# Display directory configuration
echo "Using directories:"
echo "Base dir: $NOVA_BASE_DIR"
echo "Input dir: $NOVA_INPUT_DIR"
echo "Processing dir: $NOVA_PROCESSING_DIR"
echo "Parse dir: $NOVA_PHASE_MARKDOWN_PARSE"

# Create required directories
echo "Creating required directories..."
mkdir -p "$NOVA_INPUT_DIR"
mkdir -p "$NOVA_PROCESSING_DIR"
mkdir -p "$NOVA_PHASE_MARKDOWN_PARSE"

# Verify directories exist
echo "Verifying directories..."
for dir in "$NOVA_INPUT_DIR" "$NOVA_PROCESSING_DIR" "$NOVA_PHASE_MARKDOWN_PARSE"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Directory $dir does not exist"
        exit 1
    fi
done

# Run the consolidation pipeline
echo "Running consolidation pipeline..."
python -m nova.pipeline.consolidate 2>&1 | while IFS= read -r line; do
    # Check for phase progress updates
    if [[ $line =~ Phase\ ([A-Z_]+):\ ([0-9]+)%\ -\ ([a-zA-Z_]+)\ -\ ([0-9]+)\ files ]]; then
        phase_id="${BASH_REMATCH[1]}"
        progress="${BASH_REMATCH[2]}"
        status="${BASH_REMATCH[3]}"
        files="${BASH_REMATCH[4]}"
        
        # Create progress bar
        bar_size=40
        completed=$((progress * bar_size / 100))
        remaining=$((bar_size - completed))
        
        # Build the progress bar string
        progress_bar="["
        for ((i=0; i<completed; i++)); do progress_bar+="="; done
        if [ $completed -lt $bar_size ]; then progress_bar+=">"; fi
        for ((i=0; i<remaining-1; i++)); do progress_bar+=" "; done
        progress_bar+="]"
        
        # Print progress with colors
        printf "\033[K\033[1;34m%-20s\033[0m %s \033[1;32m%3d%%\033[0m \033[1;33m%-12s\033[0m \033[1;36m%d files\033[0m\r" \
            "$phase_id" "$progress_bar" "$progress" "$status" "$files"
    elif [[ $line =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
        # Timestamp line - print on new line
        echo -e "\n$line"
    elif [[ $line == *"Successfully"* ]]; then
        # Success message - print on new line with color
        echo -e "\n\033[1;32m$line\033[0m"
    elif [[ $line == *"ERROR"* || $line == *"Error"* || $line == *"error"* ]]; then
        # Error message - print on new line with color
        echo -e "\n\033[1;31m$line\033[0m"
    elif [[ $line == *"WARNING"* || $line == *"Warning"* || $line == *"warning"* ]]; then
        # Warning message - print on new line with color
        echo -e "\n\033[1;33m$line\033[0m"
    else
        # Other lines - print normally
        echo "$line"
    fi
done

# Check exit status
exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "Pipeline failed with exit status $exit_status"
    exit $exit_status
fi