#!/bin/bash

# Exit on error
set -e

# Print initialization header
echo "───────────────────────────────────── Initialization Phase ────────────────────────────────────"
echo

# Source environment variables
set -a  # Enable automatic export of variables
source .env
set +a  # Disable automatic export

# Check environment variables
echo "Loading environment variables from .env"
echo "OPEN_AI_KEY is set: $([ ! -z "$OPEN_AI_KEY" ] && echo "yes" || echo "no")"
echo "OpenAI API key is set: $([ ! -z "$OPENAI_API_KEY" ] && echo "yes" || echo "no")"

if [ ! -z "$OPEN_AI_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Using OPEN_AI_KEY as OPENAI_API_KEY"
    export OPENAI_API_KEY="$OPEN_AI_KEY"
fi

# Create required directories
echo "Creating required directories..."

# Base directories
mkdir -p "${NOVA_BASE_DIR:?NOVA_BASE_DIR not set}"

# Phase directory
mkdir -p "${NOVA_PHASE_MARKDOWN_PARSE:?NOVA_PHASE_MARKDOWN_PARSE not set}"

# Image processing directories
mkdir -p "${NOVA_ORIGINAL_IMAGES_DIR:?NOVA_ORIGINAL_IMAGES_DIR not set}"
mkdir -p "${NOVA_PROCESSED_IMAGES_DIR:?NOVA_PROCESSED_IMAGES_DIR not set}"
mkdir -p "${NOVA_IMAGE_METADATA_DIR:?NOVA_IMAGE_METADATA_DIR not set}"
mkdir -p "${NOVA_IMAGE_CACHE_DIR:?NOVA_IMAGE_CACHE_DIR not set}"

# Office document directories
mkdir -p "${NOVA_OFFICE_ASSETS_DIR:?NOVA_OFFICE_ASSETS_DIR not set}"
mkdir -p "${NOVA_OFFICE_TEMP_DIR:?NOVA_OFFICE_TEMP_DIR not set}"

# Function to show usage
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --force, -f        Force processing of all files"
    echo "  --dry-run, -n      Show what would be processed without processing"
    echo "  --show-state, -s   Display current processing state"
    echo "  --scan             Show directory structure"
    echo "  --reset            Reset processing state"
    echo "  --log-level        Set logging level (DEBUG|INFO|WARNING|ERROR)"
    echo "  --help, -h         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Normal processing"
    echo "  $0 --force             # Force reprocess all files"
    echo "  $0 --dry-run           # Show what would be processed"
    echo "  $0 --show-state        # Show current state"
    echo "  $0 --scan              # Show directory structure"
}

# Parse command line arguments
ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            ARGS="$ARGS --force"
            shift
            ;;
        --dry-run|-n)
            ARGS="$ARGS --dry-run"
            shift
            ;;
        --show-state|-s)
            ARGS="$ARGS --show-state"
            shift
            ;;
        --scan)
            ARGS="$ARGS --scan"
            shift
            ;;
        --reset)
            ARGS="$ARGS --reset"
            shift
            ;;
        --log-level)
            if [ -z "$2" ] || [[ "$2" == -* ]]; then
                echo "Error: --log-level requires a value"
                exit 1
            fi
            ARGS="$ARGS --log-level $2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Header for Nova Document Processor
echo
echo "───────────────────────────────────── Nova Document Processor ────────────────────────────────────"
echo

# Run the processor with environment variables and any passed arguments
NOVA_BASE_DIR="$NOVA_BASE_DIR" \
NOVA_INPUT_DIR="$NOVA_INPUT_DIR" \
NOVA_OUTPUT_DIR="$NOVA_OUTPUT_DIR" \
NOVA_CONFIG_DIR="$NOVA_CONFIG_DIR" \
NOVA_PROCESSING_DIR="$NOVA_PROCESSING_DIR" \
NOVA_TEMP_DIR="$NOVA_TEMP_DIR" \
NOVA_PHASE_MARKDOWN_PARSE="$NOVA_PHASE_MARKDOWN_PARSE" \
NOVA_OFFICE_ASSETS_DIR="$NOVA_OFFICE_ASSETS_DIR" \
NOVA_OFFICE_TEMP_DIR="$NOVA_OFFICE_TEMP_DIR" \
poetry run python -m src.nova.cli.main $ARGS

exit_code=$?

case $exit_code in
    0)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Processing completed successfully"
        exit 0
        ;;
    1)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Critical error occurred during processing"
        exit 1
        ;;
    2)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Processing completed with warnings"
        exit 0
        ;;
    *)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Unknown error occurred (exit code: $exit_code)"
        exit 1
        ;;
esac