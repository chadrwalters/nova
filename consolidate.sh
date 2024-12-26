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
    if [[ $line == *"Phase"* && $line == *"progress:"* ]]; then
        # Extract phase information
        phase_id=$(echo "$line" | grep -o 'Phase [^:]*' | cut -d' ' -f2)
        progress=$(echo "$line" | grep -o '[0-9]*\.[0-9]*%')
        status=$(echo "$line" | grep -o '[a-z_]*$')
        
        # Create progress bar
        progress_val=${progress%.*}
        bar_size=50
        completed=$((progress_val * bar_size / 100))
        remaining=$((bar_size - completed))
        
        # Build the progress bar string
        progress_bar="["
        for ((i=0; i<completed; i++)); do progress_bar+="="; done
        if [ $completed -lt $bar_size ]; then progress_bar+=">"; fi
        for ((i=0; i<remaining-1; i++)); do progress_bar+=" "; done
        progress_bar+="]"
        
        # Print progress with colors
        printf "\033[K\033[1;34mPhase %s\033[0m %s \033[1;32m%s\033[0m \033[1;33m%s\033[0m\r" \
            "$phase_id" "$progress_bar" "$progress" "$status"
    elif [[ $line == *"Summary"* ]]; then
        # Print pipeline summary
        echo -e "\n\n$line"
    else
        # Print other lines normally
        echo "$line"
    fi
done

# Check exit status
exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "Pipeline failed with exit status $exit_status"
    exit $exit_status
fi