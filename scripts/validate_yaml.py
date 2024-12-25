#!/usr/bin/env python3
"""Validate YAML configuration files for Nova document processor."""

import sys
from pathlib import Path
import argparse
from typing import List, Optional

from nova.core.utils.yaml_validator import YAMLValidator
from nova.core.logging import get_logger

logger = get_logger(__name__)

def validate_files(files: List[str], verbose: bool = False) -> bool:
    """Validate YAML configuration files.
    
    Args:
        files: List of files to validate
        verbose: Whether to show detailed output
        
    Returns:
        bool: True if all files are valid
    """
    validator = YAMLValidator()
    all_valid = True
    
    for file_path in files:
        if verbose:
            print(f"\nValidating {file_path}...")
            
        is_valid = validator.validate_file(file_path)
        report = validator.get_validation_report()
        
        if not is_valid:
            all_valid = False
            print(f"\nErrors in {file_path}:")
            for error in report['errors']:
                print(f"  - {error}")
                
        if verbose and report['warnings']:
            print(f"\nWarnings for {file_path}:")
            for warning in report['warnings']:
                print(f"  - {warning}")
                
    return all_valid

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate YAML configuration files"
    )
    parser.add_argument(
        'files',
        nargs='+',
        help="YAML files to validate"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    try:
        is_valid = validate_files(args.files, args.verbose)
        if is_valid:
            print("\nAll files are valid!")
            sys.exit(0)
        else:
            print("\nValidation failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(2)

if __name__ == '__main__':
    main() 