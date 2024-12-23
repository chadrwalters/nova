#!/bin/bash

# Create a temporary Python environment directory
TEMP_PYTHON_ENV="/tmp/nova_env_$$"
mkdir -p "${TEMP_PYTHON_ENV}"

# Create Python startup file to suppress warnings
cat > "${TEMP_PYTHON_ENV}/sitecustomize.py" << 'EOF'
import warnings
import sys
import re

# Completely disable all deprecation warnings from importlib._bootstrap
warnings.filterwarnings('ignore', category=DeprecationWarning, module='importlib._bootstrap')

# Disable SWIG-related deprecation warnings
def ignore_swig_warnings(message, category, filename, lineno, file=None, line=None):
    if category == DeprecationWarning:
        if any(x in str(message).lower() for x in ['swigpy', 'swig', 'builtin type']):
            return
    return _original_showwarning(message, category, filename, lineno, file, line)

# Store original warning handler and replace it
_original_showwarning = warnings.showwarning
warnings.showwarning = ignore_swig_warnings

# Additional warning filters
warnings.filterwarnings('ignore', category=ImportWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning, module='_warnings')
EOF

# Set up Python environment
export PYTHONPATH="${TEMP_PYTHON_ENV}:${PWD}"
export PYTHONWARNINGS="ignore::DeprecationWarning"

# Create a wrapper script to run Python with warning filters
cat > "${TEMP_PYTHON_ENV}/run_with_filters.py" << 'EOF'
import sys
import warnings

# Apply warning filters before importing anything else
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=ImportWarning)

# Import and run the actual script
if len(sys.argv) > 1:
    import runpy
    runpy.run_path(sys.argv[1], run_name='__main__')
EOF

# Function to clean up temporary Python environment
cleanup() {
    rm -rf "${TEMP_PYTHON_ENV}"
}
trap cleanup EXIT

# Exit on error
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print initialization header
echo -e "${BLUE}${BOLD}───────────────────────────────────── Initialization Phase ────────────────────────────────────${NC}"
echo

# Source environment variables
set -a  # Enable automatic export of variables
source .env
set +a  # Disable automatic export

# Print environment variables for debugging
echo "Environment variables:"
echo "NOVA_BASE_DIR=$NOVA_BASE_DIR"
echo "NOVA_INPUT_DIR=$NOVA_INPUT_DIR"
echo "NOVA_OUTPUT_DIR=$NOVA_OUTPUT_DIR"
echo "NOVA_PROCESSING_DIR=$NOVA_PROCESSING_DIR"
echo "NOVA_TEMP_DIR=$NOVA_TEMP_DIR"
echo "NOVA_PHASE_MARKDOWN_PARSE=$NOVA_PHASE_MARKDOWN_PARSE"
echo "NOVA_PHASE_MARKDOWN_CONSOLIDATE=$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
echo "NOVA_PHASE_MARKDOWN_AGGREGATE=$NOVA_PHASE_MARKDOWN_AGGREGATE"
echo "NOVA_PHASE_MARKDOWN_SPLIT=$NOVA_PHASE_MARKDOWN_SPLIT"
echo "NOVA_ORIGINAL_IMAGES_DIR=$NOVA_ORIGINAL_IMAGES_DIR"
echo "NOVA_PROCESSED_IMAGES_DIR=$NOVA_PROCESSED_IMAGES_DIR"
echo "NOVA_IMAGE_METADATA_DIR=$NOVA_IMAGE_METADATA_DIR"
echo "NOVA_IMAGE_CACHE_DIR=$NOVA_IMAGE_CACHE_DIR"
echo "NOVA_OFFICE_ASSETS_DIR=$NOVA_OFFICE_ASSETS_DIR"
echo "NOVA_OFFICE_TEMP_DIR=$NOVA_OFFICE_TEMP_DIR"

# Create required directories with proper permissions
echo -e "\n${CYAN}Creating required directories...${NC}"

# Image processing directories
echo -e "${DIM}Creating image processing directories...${NC}"
for dir in "${NOVA_ORIGINAL_IMAGES_DIR}" "${NOVA_PROCESSED_IMAGES_DIR}" "${NOVA_IMAGE_METADATA_DIR}" "${NOVA_IMAGE_CACHE_DIR}"; do
    mkdir -p "$dir"
    chmod 755 "$dir"
done

# Base directories
echo -e "${DIM}Creating base directory...${NC}"
mkdir -p "${NOVA_BASE_DIR:?NOVA_BASE_DIR not set}"

# Phase directories
echo -e "${DIM}Creating phase directories...${NC}"
for dir in "${NOVA_PHASE_MARKDOWN_PARSE}" "${NOVA_PHASE_MARKDOWN_CONSOLIDATE}" "${NOVA_PHASE_MARKDOWN_AGGREGATE}" "${NOVA_PHASE_MARKDOWN_SPLIT}"; do
    mkdir -p "$dir"
    chmod 755 "$dir"
done

# Office document directories
echo -e "${DIM}Creating office document directories...${NC}"
for dir in "${NOVA_OFFICE_ASSETS_DIR}" "${NOVA_OFFICE_TEMP_DIR}"; do
    mkdir -p "$dir"
    chmod 755 "$dir"
done

# Check environment variables
echo -e "${CYAN}Loading environment variables from .env${NC}"
echo -e "${DIM}OPEN_AI_KEY is set: $([ ! -z "$OPEN_AI_KEY" ] && echo "yes" || echo "no")${NC}"
echo -e "${DIM}OpenAI API key is set: $([ ! -z "$OPENAI_API_KEY" ] && echo "yes" || echo "no")${NC}"

if [ ! -z "$OPEN_AI_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Using OPEN_AI_KEY as OPENAI_API_KEY${NC}"
    export OPENAI_API_KEY="$OPEN_AI_KEY"
fi

# Function to show usage
show_help() {
    echo -e "${BLUE}${BOLD}Usage: $0 [options]${NC}"
    echo
    echo -e "${BOLD}Options:${NC}"
    echo -e "  ${CYAN}--force, -f${NC}        Force processing of all files"
    echo -e "  ${CYAN}--dry-run, -n${NC}      Show what would be processed without processing"
    echo -e "  ${CYAN}--show-state, -s${NC}   Display current processing state"
    echo -e "  ${CYAN}--scan${NC}             Show directory structure"
    echo -e "  ${CYAN}--reset${NC}            Reset processing state"
    echo -e "  ${CYAN}--log-level${NC}        Set logging level (DEBUG|INFO|WARNING|ERROR)"
    echo -e "  ${CYAN}--help, -h${NC}         Show this help message"
    echo
    echo -e "${BOLD}Examples:${NC}"
    echo -e "  ${DIM}$0                      # Normal processing${NC}"
    echo -e "  ${DIM}$0 --force             # Force reprocess all files${NC}"
    echo -e "  ${DIM}$0 --dry-run           # Show what would be processed${NC}"
    echo -e "  ${DIM}$0 --show-state        # Show current state${NC}"
    echo -e "  ${DIM}$0 --scan              # Show directory structure${NC}"
}

# Parse command line arguments
ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            ARGS="$ARGS --force"
            echo -e "${YELLOW}Force processing enabled${NC}"
            shift
            ;;
        --dry-run|-n)
            ARGS="$ARGS --dry-run"
            echo -e "${YELLOW}Dry run mode enabled${NC}"
            shift
            ;;
        --show-state|-s)
            ARGS="$ARGS --show-state"
            echo -e "${CYAN}Showing current state${NC}"
            shift
            ;;
        --scan)
            ARGS="$ARGS --scan"
            echo -e "${CYAN}Scanning directory structure${NC}"
            shift
            ;;
        --reset)
            ARGS="$ARGS --reset"
            echo -e "${YELLOW}Resetting processing state${NC}"
            shift
            ;;
        --log-level)
            if [ -z "$2" ] || [[ "$2" == -* ]]; then
                echo -e "${RED}Error: --log-level requires a value${NC}"
                exit 1
            fi
            ARGS="$ARGS --log-level $2"
            echo -e "${CYAN}Setting log level to: $2${NC}"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Header for Nova Document Processor
echo
echo -e "${BLUE}${BOLD}───────────────────────────────────── Nova Document Processor ────────────────────────────────────${NC}"
echo

# Run the processor with environment variables and any passed arguments
echo -e "${CYAN}Starting Nova Document Processor...${NC}"
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
        echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Processing completed successfully${NC}"
        exit 0
        ;;
    1)
        echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Critical error occurred during processing${NC}"
        exit 1
        ;;
    2)
        echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Processing completed with warnings${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Unknown error occurred (exit code: $exit_code)${NC}"
        exit 1
        ;;
esac

git checkout -b refactor-backup
git add .
git commit -m "Create backup branch before refactoring processors"
git push origin refactor-backup

git checkout main
git checkout -b refactor-processors