#!/bin/zsh

# setup.sh - Initialize development environment for Nova markdown tools

set -e  # Exit on error
set -u  # Exit on undefined variable

# Function to print status with rich formatting
print_status() {
    python3 -c "from rich import print; print('$1')" 2>/dev/null || echo "$1"
}

# Check Python installation
if ! command -v python3 &> /dev/null; then
    print_status "[red]✗ Error:[/] Python 3 is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    print_status "[yellow]Creating virtual environment...[/]"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
print_status "[cyan]Upgrading pip...[/]"
pip install --upgrade pip >/dev/null 2>&1

# Install dependencies
print_status "[cyan]Installing dependencies...[/]"
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [[ ! -f ".env" ]]; then
    print_status "[yellow]Creating .env file from template...[/]"
    cp .env.template .env
fi

print_status "[green]✓ Setup complete![/]"
print_status "\nTo get started:"
print_status "1. Edit .env file with your configuration"
print_status "2. Run ./consolidate.sh to process markdown files" 