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

NOVA_HOME=~/.nova
NOVA_LOCAL=.nova

echo "🗑️  Removing Nova system directories..."
# Only try to remove if they exist and we have permission
[ -d "$NOVA_HOME" ] && [ -w "$NOVA_HOME" ] && rm -rf "$NOVA_HOME"
[ -d "$NOVA_LOCAL" ] && [ -w "$NOVA_LOCAL" ] && rm -rf "$NOVA_LOCAL"

# Ensure base directories exist with proper permissions
echo "📁 Creating base directories..."
for DIR in $NOVA_HOME $NOVA_LOCAL; do
    mkdir -p "$DIR/vectors" "$DIR/cache" "$DIR/logs" "$DIR/processing"
    # Ensure we have write permissions
    chmod -R u+w "$DIR"
done

# Initialize ChromaDB
echo "💾 Initializing ChromaDB..."
uv run python -m nova.cli monitor health >/dev/null 2>&1 || true

echo "🧹 Cleaning system..."
echo "Cleaning vectors..."
# Only show console output, filter out debug messages
uv run python -m nova.cli clean-vectors --force 2>/dev/null | grep -v "DEBUG:" || true

echo "Cleaning processing directory..."
# Only show console output, filter out debug messages
uv run python -m nova.cli clean-processing --force 2>/dev/null | grep -v "DEBUG:" || true

echo "📝 Processing notes..."
# Only show progress bars and errors, filter out debug messages
uv run python -m nova.cli process-notes --input-dir "/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput" 2>&1 | grep -E "Converting files|Error:" | grep -v "DEBUG:" || true

echo "🔄 Processing vectors..."
# Only show progress bars and errors, filter out debug messages
uv run python -m nova.cli process-vectors --text .nova/processing --output-dir .nova/vectors 2>&1 | grep -E "Adding chunks|Error:" | grep -v "DEBUG:" || true

echo "🏥 Checking system health..."
uv run python -m nova.cli monitor health 2>&1 | grep -E "✅|❌" || true

echo "📊 System statistics:"
echo "Vector Store Stats:"
uv run python -m nova.cli monitor stats 2>&1 | sed -n '/Vector Store Statistics:/,/Log Statistics:/p' | grep -E "Documents|Total|Cache|Last" | grep -v "Log Statistics:"

echo "Log Stats:"
uv run python -m nova.cli monitor stats 2>&1 | sed -n '/Log Statistics:/,$p' | grep -E "Total|Error|Warning|Info"

echo "✅ Rebuild complete! System is ready for Claude integration."
