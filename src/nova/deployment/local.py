#!/usr/bin/env python3
"""Local deployment script for Nova."""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


def validate_environment() -> bool:
    """Validate required environment variables and dependencies."""
    required_vars = ["ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


def validate_config(config_path: Path) -> bool:
    """Validate Nova configuration file."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        required_sections = ["ingestion", "embedding", "vector_store", "rag", "llm", "security"]
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            print(f"Missing required config sections: {', '.join(missing_sections)}")
            return False
            
        return True
    except Exception as e:
        print(f"Error validating config: {e}")
        return False


def setup_directories() -> bool:
    """Create required directories if they don't exist."""
    required_dirs = [
        "cache",
        "logs",
        "output",
        "data/vectors",
        "data/backup"
    ]
    
    try:
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False


def deploy_local(config_path: Optional[Path] = None) -> bool:
    """Deploy Nova locally."""
    # Load environment variables
    load_dotenv()
    
    # Validate environment
    if not validate_environment():
        return False
        
    # Validate config if provided
    if config_path and not validate_config(config_path):
        return False
        
    # Setup directories
    if not setup_directories():
        return False
        
    print("Local deployment completed successfully!")
    return True


if __name__ == "__main__":
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    success = deploy_local(config_path)
    sys.exit(0 if success else 1) 