#!/bin/bash

# Nova System Rebuild Script
# This script performs a complete rebuild of the Nova system:
# 1. Removes all Nova system directories and files
# 2. Cleans all data through CLI
# 3. Processes notes
# 4. Builds vectors
# 5. Verifies health
# 6. Reports stats

set -e  # Exit on any error

# Load environment configuration
if [ -f .env.local ]; then
    source .env.local
elif [ -f .env ]; then
    source .env
fi

# Function to handle errors
handle_error() {
    local step=$1
    local exit_code=$2
    echo "❌ Error during $step (exit code: $exit_code)"
    uv run python -m nova.cli monitor health || true
    exit $exit_code
}

# Check input directory
if [ ! -d "${NOVA_INPUT}" ]; then
    echo "❌ Error: Input directory '${NOVA_INPUT}' does not exist"
    exit 1
fi

if [ ! -r "${NOVA_INPUT}" ]; then
    echo "❌ Error: Cannot read input directory '${NOVA_INPUT}'"
    exit 1
fi

echo "🔄 Starting Nova system rebuild..."

echo "🧹 Cleaning system..."
echo "Cleaning vectors..."
uv run python -m nova.cli clean-vectors --force || handle_error "vector cleaning" $?

echo "Cleaning processing directory..."
uv run python -m nova.cli clean-processing --force || handle_error "processing directory cleaning" $?

echo "📝 Processing notes..."
uv run python -m nova.cli process-notes \
    --input-dir "${NOVA_INPUT}" || handle_error "note processing" $?

# Check progress after note processing
uv run python -m nova.cli monitor health || true

echo "🔄 Processing vectors..."
uv run python -m nova.cli process-vectors || handle_error "vector processing" $?

# Check progress after vector processing
uv run python -m nova.cli monitor health || true

echo "🏥 Checking system health..."
uv run python -m nova.cli monitor health || handle_error "health check" $?

echo "📊 System Report"
echo "================"

echo "Vector Store Statistics:"
uv run python -m nova.cli monitor stats || true

echo "✅ Rebuild complete! System is ready."
