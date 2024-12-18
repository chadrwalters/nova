#!/bin/zsh

# setup.sh - Initialize development environment for Nova markdown tools

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print status with color
print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Check Python installation
if ! command -v python3 &> /dev/null; then
    print_status "$RED" "✗ Error: Python 3 is required but not installed"
    exit 1
fi

# Check Poetry installation and install if needed
if ! command -v poetry &> /dev/null; then
    print_status "$YELLOW" "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Add Poetry to PATH
    case "$SHELL" in
        */zsh)
            SHELL_PROFILE="$HOME/.zshrc"
            ;;
        */bash)
            SHELL_PROFILE="$HOME/.bashrc"
            ;;
        *)
            SHELL_PROFILE="$HOME/.profile"
            ;;
    esac

    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_PROFILE"
    source "$SHELL_PROFILE"
fi

# Install dependencies
print_status "$CYAN" "Installing dependencies..."
poetry install

# Create required directories
print_status "$CYAN" "Creating directory structure..."

# Load environment variables
if [ -f .env ]; then
    source .env
else
    print_status "$YELLOW" "Creating .env file from template..."
    cp .env.template .env
    source .env
fi

# Export environment variables
export SYNC_BASE
export NOVA_INPUT_DIR
export NOVA_OUTPUT_DIR
export NOVA_PROCESSING_DIR
export NOVA_TEMPLATE_DIR
export NOVA_CONFIG_DIR
export NOVA_ERROR_TOLERANCE
export NOVA_MAX_FILE_SIZE_MB
export NOVA_MAX_MEMORY_PERCENT
export NOVA_CONCURRENT_PROCESSES
export DYLD_LIBRARY_PATH

# Create directories
mkdir -p "${NOVA_INPUT_DIR}"
mkdir -p "${NOVA_OUTPUT_DIR}"
mkdir -p "${NOVA_PROCESSING_DIR}"
mkdir -p "${NOVA_TEMPLATE_DIR}"

# Copy templates and config
print_status "$CYAN" "Copying templates and configuration..."

# First ensure our source directories exist
mkdir -p "src/resources/templates"
mkdir -p "src/resources/config"

# Create template files if they don't exist
if [ ! -f "src/resources/templates/pdf_template.html" ]; then
    cat > "src/resources/templates/pdf_template.html" << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
</head>
<body>
    <div class="document">
        <!-- Title Page -->
        <div class="title-page">
            <h1>{{ title }}</h1>
            {% if metadata.authors %}
            <div class="authors">
                {% for author in metadata.authors %}
                <p>{{ author }}</p>
                {% endfor %}
            </div>
            {% endif %}
            <p class="date">{{ date }}</p>
        </div>

        <!-- Table of Contents -->
        {% if toc %}
        <div class="toc">
            <h2>Table of Contents</h2>
            <!-- WeasyPrint will auto-generate TOC here -->
        </div>
        {% endif %}

        <!-- Main Content -->
        <div class="content">
            {{ content | safe }}
        </div>
    </div>
</body>
</html>
EOL
fi

if [ ! -f "src/resources/templates/pdf_styles.css" ]; then
    cat > "src/resources/templates/pdf_styles.css" << 'EOL'
/* Base styles */
@page {
    margin: 2.5cm 1.5cm;
    size: A4;
    @bottom-right {
        content: counter(page);
    }
}

/* Title page */
.title-page {
    page-break-after: always;
    text-align: center;
    margin-top: 30%;
}

.title-page h1 {
    font-size: 24pt;
    margin-bottom: 2cm;
}

.authors {
    margin: 1cm 0;
}

.date {
    margin-top: 2cm;
}

/* Table of Contents */
.toc {
    page-break-after: always;
}

.toc a {
    text-decoration: none;
    color: black;
}

/* Content */
body {
    font-family: "DejaVu Serif", serif;
    font-size: 11pt;
    line-height: 1.6;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "DejaVu Sans", sans-serif;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

h1 { font-size: 20pt; }
h2 { font-size: 16pt; }
h3 { font-size: 14pt; }
h4 { font-size: 12pt; }

/* Code blocks */
pre {
    background-color: #f5f5f5;
    padding: 1em;
    margin: 1em 0;
    border: 1px solid #ddd;
    border-radius: 4px;
    white-space: pre-wrap;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 9pt;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
}

th {
    background-color: #f5f5f5;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    margin: 1em 0;
}

/* Page breaks */
h1 {
    page-break-before: always;
}

.content > h1:first-child {
    page-break-before: avoid;
}

table, pre, img {
    page-break-inside: avoid;
}
EOL
fi

if [ ! -f "src/resources/config/default_config.yaml" ]; then
    cat > "src/resources/config/default_config.yaml" << 'EOL'
# Nova Default Configuration

# Processing Options
processing:
  error_tolerance: "lenient"  # "strict" or "lenient"
  max_file_size_mb: 50
  max_memory_percent: 75
  concurrent_processes: 4

# Document Style
style:
  page_size: "A4"
  margin: "2.5cm 1.5cm"
  font_family: "DejaVu Serif"
  font_size: "11pt"
  line_height: "1.6"
  colors:
    text: "#333333"
    headings: "#000000"
    links: "#0066cc"
    code_background: "#f5f5f5"
    table_border: "#dddddd"

# Markdown Processing
markdown:
  extensions:
    - extra
    - codehilite
    - tables
    - toc
    - fenced_code
    - sane_lists

# PDF Generation
pdf:
  metadata:
    creator: "Nova Document Processor"
    producer: "WeasyPrint"
  compression: true
  attachments:
    embed: true
    max_size_mb: 20
EOL
fi

# Now copy the files to their destinations
poetry run python -c "
from pathlib import Path
import shutil
import os
import sys

def safe_copy(src: Path, dst: Path) -> None:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src != dst:
            print(f'Copying {src} to {dst}')
            shutil.copy2(src, dst)
    except Exception as e:
        print(f'Error copying {src} to {dst}: {e}', file=sys.stderr)
        raise

# Print environment variables for debugging
print('Environment variables:')
for var in ['NOVA_TEMPLATE_DIR', 'NOVA_PROCESSING_DIR']:
    print(f'{var}: {os.environ.get(var, 'NOT SET')}')

# Copy templates
template_src = Path('src/resources/templates')
template_dst = Path(os.environ.get('NOVA_TEMPLATE_DIR', 'templates'))

for template in template_src.glob('*.*'):
    safe_copy(template, template_dst / template.name)

# Copy config
config_src = Path('src/resources/config')
config_dst = Path(os.environ.get('NOVA_PROCESSING_DIR', 'processing')) / 'config'

for config in config_src.glob('*.yaml'):
    safe_copy(config, config_dst / config.name)
"

print_status "$GREEN" "✓ Setup completed successfully!"
print_status "$CYAN" "
Directory Structure:
  ${NOVA_INPUT_DIR}/         (Source markdown files)
  ${NOVA_OUTPUT_DIR}/        (Final PDF output)
  ${NOVA_PROCESSING_DIR}/    (Processing files)
  ${NOVA_TEMPLATE_DIR}/      (HTML/PDF templates)
"
