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

# Check Poetry installation and add to PATH if needed
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

    # Add Poetry PATH to shell profile if not already present
    POETRY_PATH="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$POETRY_PATH:"* ]]; then
        echo "export PATH=\"$POETRY_PATH:\$PATH\"" >> "$SHELL_PROFILE"
        export PATH="$POETRY_PATH:$PATH"
        print_status "$YELLOW" "Added Poetry to PATH in $SHELL_PROFILE"
        print_status "$YELLOW" "Please restart your terminal or run: source $SHELL_PROFILE"
    fi
fi

# Verify Poetry is now available
if ! command -v poetry &> /dev/null; then
    print_status "$RED" "✗ Error: Poetry installation failed or not in PATH"
    print_status "$YELLOW" "Please try running:"
    print_status "$YELLOW" "export PATH=\"\$HOME/.local/bin:\$PATH\""
    print_status "$YELLOW" "Then run this script again."
    exit 1
fi

# Install dependencies using Poetry
print_status "$CYAN" "Installing dependencies with Poetry..."
poetry install

# Create .env file if it doesn't exist
if [[ ! -f ".env" ]]; then
    print_status "$YELLOW" "Creating .env file from template..."
    cp .env.template .env
fi

# Pre-commit hooks installation removed for now

print_status "$GREEN" "✓ Setup complete!"
echo
print_status "$NC" "To get started:"
print_status "$NC" "1. Edit .env file with your configuration"
print_status "$NC" "2. Run ./consolidate.sh to process markdown files"
print_status "$NC" "3. Activate the virtual environment with: poetry shell"

# If we added Poetry to PATH during this run, remind user to reload shell
if [[ -n "${POETRY_PATH:-}" ]]; then
    echo
    print_status "$YELLOW" "Important: To use Poetry in this terminal session, please run:"
    print_status "$YELLOW" "source $SHELL_PROFILE"
fi
