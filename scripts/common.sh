#!/bin/bash

# Source environment variables
source .env 2>/dev/null || true

# Validate environment variables
validate_env_vars() {
    echo "Validating environment variables..."
    
    # Required directories
    NOVA_BASE_DIR="${NOVA_BASE_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs}"
    NOVA_INPUT_DIR="${NOVA_INPUT_DIR:-$NOVA_BASE_DIR/_NovaInput}"
    NOVA_PROCESSING_DIR="${NOVA_PROCESSING_DIR:-$NOVA_BASE_DIR/_NovaProcessing}"
    NOVA_TEMP_DIR="${NOVA_TEMP_DIR:-$NOVA_PROCESSING_DIR/temp}"
    
    # Phase directories
    NOVA_PHASE_MARKDOWN_PARSE="${NOVA_PHASE_MARKDOWN_PARSE:-$NOVA_PROCESSING_DIR/phases/markdown_parse}"
    NOVA_PHASE_MARKDOWN_CONSOLIDATE="${NOVA_PHASE_MARKDOWN_CONSOLIDATE:-$NOVA_PROCESSING_DIR/phases/markdown_consolidate}"
    NOVA_PHASE_MARKDOWN_AGGREGATE="${NOVA_PHASE_MARKDOWN_AGGREGATE:-$NOVA_PROCESSING_DIR/phases/markdown_aggregate}"
    NOVA_PHASE_MARKDOWN_SPLIT="${NOVA_PHASE_MARKDOWN_SPLIT:-$NOVA_PROCESSING_DIR/phases/markdown_split}"
    
    # Image directories
    NOVA_ORIGINAL_IMAGES_DIR="${NOVA_ORIGINAL_IMAGES_DIR:-$NOVA_PROCESSING_DIR/images/original}"
    NOVA_PROCESSED_IMAGES_DIR="${NOVA_PROCESSED_IMAGES_DIR:-$NOVA_PROCESSING_DIR/images/processed}"
    NOVA_IMAGE_METADATA_DIR="${NOVA_IMAGE_METADATA_DIR:-$NOVA_PROCESSING_DIR/images/metadata}"
    NOVA_IMAGE_CACHE_DIR="${NOVA_IMAGE_CACHE_DIR:-$NOVA_PROCESSING_DIR/images/cache}"
    
    # Office directories
    NOVA_OFFICE_ASSETS_DIR="${NOVA_OFFICE_ASSETS_DIR:-$NOVA_PROCESSING_DIR/office/assets}"
    NOVA_OFFICE_TEMP_DIR="${NOVA_OFFICE_TEMP_DIR:-$NOVA_PROCESSING_DIR/office/temp}"
    
    # Export all variables
    export NOVA_BASE_DIR
    export NOVA_INPUT_DIR
    export NOVA_PROCESSING_DIR
    export NOVA_TEMP_DIR
    export NOVA_PHASE_MARKDOWN_PARSE
    export NOVA_PHASE_MARKDOWN_CONSOLIDATE
    export NOVA_PHASE_MARKDOWN_AGGREGATE
    export NOVA_PHASE_MARKDOWN_SPLIT
    export NOVA_ORIGINAL_IMAGES_DIR
    export NOVA_PROCESSED_IMAGES_DIR
    export NOVA_IMAGE_METADATA_DIR
    export NOVA_IMAGE_CACHE_DIR
    export NOVA_OFFICE_ASSETS_DIR
    export NOVA_OFFICE_TEMP_DIR
}

# Show directories being used
show_directories() {
    echo "Using directories:"
    echo "Base dir: $NOVA_BASE_DIR"
    echo "Input dir: $NOVA_INPUT_DIR"
    echo "Processing dir: $NOVA_PROCESSING_DIR"
    echo "Temp dir: $NOVA_TEMP_DIR"
}

# Create required directories
create_directories() {
    echo "Creating required directories..."
    
    # Create base directories
    mkdir -p "$NOVA_INPUT_DIR"
    mkdir -p "$NOVA_PROCESSING_DIR"
    mkdir -p "$NOVA_TEMP_DIR"
    
    # Create phase directories
    mkdir -p "$NOVA_PHASE_MARKDOWN_PARSE"
    mkdir -p "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
    mkdir -p "$NOVA_PHASE_MARKDOWN_AGGREGATE"
    mkdir -p "$NOVA_PHASE_MARKDOWN_SPLIT"
    
    # Create image directories
    mkdir -p "$NOVA_ORIGINAL_IMAGES_DIR"
    mkdir -p "$NOVA_PROCESSED_IMAGES_DIR"
    mkdir -p "$NOVA_IMAGE_METADATA_DIR"
    mkdir -p "$NOVA_IMAGE_CACHE_DIR"
    
    # Create office directories
    mkdir -p "$NOVA_OFFICE_ASSETS_DIR"
    mkdir -p "$NOVA_OFFICE_TEMP_DIR"
}

# Verify directories exist
verify_directories() {
    echo "Verifying directories..."
    
    # List of all directories to verify
    local dirs=(
        "$NOVA_INPUT_DIR"
        "$NOVA_PROCESSING_DIR"
        "$NOVA_TEMP_DIR"
        "$NOVA_PHASE_MARKDOWN_PARSE"
        "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
        "$NOVA_PHASE_MARKDOWN_AGGREGATE"
        "$NOVA_PHASE_MARKDOWN_SPLIT"
        "$NOVA_ORIGINAL_IMAGES_DIR"
        "$NOVA_PROCESSED_IMAGES_DIR"
        "$NOVA_IMAGE_METADATA_DIR"
        "$NOVA_IMAGE_CACHE_DIR"
        "$NOVA_OFFICE_ASSETS_DIR"
        "$NOVA_OFFICE_TEMP_DIR"
    )
    
    # Check each directory
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            echo "Error: Directory $dir does not exist"
            exit 1
        fi
    done
}

# Format progress bar
format_progress_bar() {
    local progress=$1
    local bar_size=40
    local completed=$((progress * bar_size / 100))
    local remaining=$((bar_size - completed))
    
    local progress_bar="["
    for ((i=0; i<completed; i++)); do progress_bar+="="; done
    if [ $completed -lt $bar_size ]; then progress_bar+=">"; fi
    for ((i=0; i<remaining-1; i++)); do progress_bar+=" "; done
    progress_bar+="]"
    
    echo "$progress_bar"
}

# Format colored output
format_colored_output() {
    local line=$1
    
    if [[ $line =~ Phase\ ([A-Z_]+):\ ([0-9]+)%\ -\ ([a-zA-Z_]+)\ -\ ([0-9]+)\ files ]]; then
        local phase_id="${BASH_REMATCH[1]}"
        local progress="${BASH_REMATCH[2]}"
        local status="${BASH_REMATCH[3]}"
        local files="${BASH_REMATCH[4]}"
        
        local progress_bar=$(format_progress_bar "$progress")
        
        printf "\033[K\033[1;34m%-20s\033[0m %s \033[1;32m%3d%%\033[0m \033[1;33m%-12s\033[0m \033[1;36m%d files\033[0m\r" \
            "$phase_id" "$progress_bar" "$progress" "$status" "$files"
    elif [[ $line =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
        echo -e "\n$line"
    elif [[ $line == *"Successfully"* ]]; then
        echo -e "\n\033[1;32m$line\033[0m"
    elif [[ $line == *"ERROR"* || $line == *"Error"* || $line == *"error"* ]]; then
        echo -e "\n\033[1;31m$line\033[0m"
    elif [[ $line == *"WARNING"* || $line == *"Warning"* || $line == *"warning"* ]]; then
        echo -e "\n\033[1;33m$line\033[0m"
    else
        echo "$line"
    fi
} 