"""Build script for Nova frontend."""

import os
import subprocess
from pathlib import Path

def build_frontend():
    """Build the frontend using npm."""
    frontend_dir = Path(__file__).parent
    
    # Install dependencies
    subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
    
    # Build the project
    subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True)

if __name__ == '__main__':
    build_frontend() 