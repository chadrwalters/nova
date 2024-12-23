#!/bin/zsh

# Source environment variables
source .env

echo "🧹 Starting cleanup process..."

# Function to safely remove directory
safe_remove() {
    if [ -d "$1" ]; then
        echo "Removing directory: $1"
        rm -rf "$1"
    fi
}

# Function to safely create directory
safe_create() {
    if [ ! -d "$1" ]; then
        echo "Creating directory: $1"
        mkdir -p "$1"
    fi
}

# Remove all processing directories
echo "Cleaning processing directories..."
safe_remove "$NOVA_PROCESSING_DIR"

# Create fresh directory structure
echo "Creating clean directory structure..."

# Create main directories
safe_create "$NOVA_PROCESSING_DIR"
safe_create "$NOVA_TEMP_DIR"

# Create phase directories
safe_create "$NOVA_PHASE_MARKDOWN_PARSE"
safe_create "$NOVA_PHASE_MARKDOWN_CONSOLIDATE"
safe_create "$NOVA_PHASE_MARKDOWN_AGGREGATE"
safe_create "$NOVA_PHASE_MARKDOWN_SPLIT"

# Create image directories
safe_create "$NOVA_ORIGINAL_IMAGES_DIR"
safe_create "$NOVA_PROCESSED_IMAGES_DIR"
safe_create "$NOVA_IMAGE_METADATA_DIR"
safe_create "$NOVA_IMAGE_CACHE_DIR"

# Create office directories
safe_create "$NOVA_OFFICE_ASSETS_DIR"
safe_create "$NOVA_OFFICE_TEMP_DIR"

# Create .state file
STATE_FILE="${NOVA_PROCESSING_DIR}/.state"
echo "Creating state file..."
cat > "$STATE_FILE" << EOL
{
    "last_update": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase_status": {
        "cleanup": "completed",
        "parse": "pending",
        "consolidate": "pending",
        "aggregate": "pending",
        "split": "pending"
    },
    "processed_files": []
}
EOL

# Verify directory structure
echo "Verifying directory structure..."
for dir in \
    "$NOVA_PROCESSING_DIR" \
    "$NOVA_TEMP_DIR" \
    "$NOVA_PHASE_MARKDOWN_PARSE" \
    "$NOVA_PHASE_MARKDOWN_CONSOLIDATE" \
    "$NOVA_PHASE_MARKDOWN_AGGREGATE" \
    "$NOVA_PHASE_MARKDOWN_SPLIT" \
    "$NOVA_ORIGINAL_IMAGES_DIR" \
    "$NOVA_PROCESSED_IMAGES_DIR" \
    "$NOVA_IMAGE_METADATA_DIR" \
    "$NOVA_IMAGE_CACHE_DIR" \
    "$NOVA_OFFICE_ASSETS_DIR" \
    "$NOVA_OFFICE_TEMP_DIR"
do
    if [ ! -d "$dir" ]; then
        echo "❌ Error: Directory not created: $dir"
        exit 1
    fi
done

# Verify state file
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ Error: State file not created"
    exit 1
fi

echo "✅ Cleanup completed successfully!"
echo "✅ Clean directory structure created!"
echo "✅ State file initialized!" 