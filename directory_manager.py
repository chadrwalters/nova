#!/usr/bin/env python3

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from datetime import datetime

class DirectoryManager:
    """Manages directory structure validation and maintenance."""
    
    def __init__(self, base_dir: Union[str, Path]):
        """Initialize the directory manager.
        
        Args:
            base_dir: Base directory path
        """
        self.base_dir = Path(base_dir)
        self.validation_log: List[Dict] = []
        self._load_environment()

    def _load_environment(self) -> None:
        """Load and validate environment variables."""
        self.required_dirs = {
            "input": os.getenv("NOVA_INPUT_DIR"),
            "output": os.getenv("NOVA_OUTPUT_DIR"),
            "processing": os.getenv("NOVA_PROCESSING_DIR"),
            "temp": os.getenv("NOVA_TEMP_DIR"),
            "phases": {
                "parse": os.getenv("NOVA_PHASE_MARKDOWN_PARSE"),
                "consolidate": os.getenv("NOVA_PHASE_MARKDOWN_CONSOLIDATE"),
                "aggregate": os.getenv("NOVA_PHASE_MARKDOWN_AGGREGATE"),
                "split": os.getenv("NOVA_PHASE_MARKDOWN_SPLIT")
            },
            "images": {
                "original": os.getenv("NOVA_ORIGINAL_IMAGES_DIR"),
                "processed": os.getenv("NOVA_PROCESSED_IMAGES_DIR"),
                "metadata": os.getenv("NOVA_IMAGE_METADATA_DIR"),
                "cache": os.getenv("NOVA_IMAGE_CACHE_DIR")
            },
            "office": {
                "assets": os.getenv("NOVA_OFFICE_ASSETS_DIR"),
                "temp": os.getenv("NOVA_OFFICE_TEMP_DIR")
            }
        }

        missing_vars = []
        self._check_missing_vars(self.required_dirs, missing_vars)
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _check_missing_vars(self, config: Dict, missing: List[str], prefix: str = "NOVA") -> None:
        """Recursively check for missing environment variables.
        
        Args:
            config: Configuration dictionary to check
            missing: List to collect missing variables
            prefix: Current prefix for variable names
        """
        for key, value in config.items():
            if isinstance(value, dict):
                self._check_missing_vars(value, missing, f"{prefix}_{key.upper()}")
            elif value is None:
                missing.append(f"{prefix}_{key.upper()}")

    def _log_validation(self, directory: Path, status: bool, message: str) -> None:
        """Log a validation check result.
        
        Args:
            directory: Directory being validated
            status: True if passed, False if failed
            message: Description or error message
        """
        self.validation_log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "directory": str(directory),
            "status": "passed" if status else "failed",
            "message": message
        })

    def validate_directory(self, path: Path) -> bool:
        """Validate a single directory.
        
        Args:
            path: Directory path to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check existence
            if not path.exists():
                self._log_validation(path, False, "Directory does not exist")
                return False

            # Check if it's a directory
            if not path.is_dir():
                self._log_validation(path, False, "Path exists but is not a directory")
                return False

            # Check permissions
            if not os.access(path, os.W_OK):
                self._log_validation(path, False, "Directory not writable")
                return False

            # Check parent directory permissions
            if not os.access(path.parent, os.W_OK):
                self._log_validation(path, False, "Parent directory not writable")
                return False

            self._log_validation(path, True, "Directory valid")
            return True

        except Exception as e:
            self._log_validation(path, False, f"Validation error: {str(e)}")
            return False

    def validate_structure(self) -> bool:
        """Validate the entire directory structure.
        
        Returns:
            bool: True if all directories are valid, False otherwise
        """
        all_valid = True
        
        def validate_group(group: Union[Dict, str], parent: Optional[Path] = None) -> bool:
            valid = True
            if isinstance(group, dict):
                for name, path in group.items():
                    if isinstance(path, dict):
                        if not validate_group(path, parent):
                            valid = False
                    else:
                        if not self.validate_directory(Path(path)):
                            valid = False
            else:
                if not self.validate_directory(Path(group)):
                    valid = False
            return valid

        return validate_group(self.required_dirs)

    def create_directory(self, path: Path) -> bool:
        """Create a directory if it doesn't exist.
        
        Args:
            path: Directory path to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self._log_validation(path, True, "Directory created")
            return True
        except Exception as e:
            self._log_validation(path, False, f"Creation error: {str(e)}")
            return False

    def create_structure(self) -> bool:
        """Create the entire directory structure.
        
        Returns:
            bool: True if all directories created successfully, False otherwise
        """
        all_created = True
        
        def create_group(group: Union[Dict, str]) -> bool:
            created = True
            if isinstance(group, dict):
                for path in group.values():
                    if isinstance(path, dict):
                        if not create_group(path):
                            created = False
                    else:
                        if not self.create_directory(Path(path)):
                            created = False
            else:
                if not self.create_directory(Path(group)):
                    created = False
            return created

        return create_group(self.required_dirs)

    def clean_directory(self, path: Path) -> bool:
        """Clean a directory by removing all contents.
        
        Args:
            path: Directory to clean
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
            self._log_validation(path, True, "Directory cleaned")
            return True
        except Exception as e:
            self._log_validation(path, False, f"Clean error: {str(e)}")
            return False

    def clean_structure(self, exclude: Optional[Set[Path]] = None) -> bool:
        """Clean the entire directory structure.
        
        Args:
            exclude: Set of directories to exclude from cleaning
            
        Returns:
            bool: True if all directories cleaned successfully, False otherwise
        """
        exclude = exclude or set()
        all_cleaned = True
        
        def clean_group(group: Union[Dict, str]) -> bool:
            cleaned = True
            if isinstance(group, dict):
                for path in group.values():
                    if isinstance(path, dict):
                        if not clean_group(path):
                            cleaned = False
                    else:
                        if Path(path) not in exclude and not self.clean_directory(Path(path)):
                            cleaned = False
            else:
                if Path(group) not in exclude and not self.clean_directory(Path(group)):
                    cleaned = False
            return cleaned

        return clean_group(self.required_dirs)

    def save_validation_report(self, output_file: Union[str, Path]) -> None:
        """Save the validation log to a file.
        
        Args:
            output_file: Path to save the report to
        """
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "validation_log": self.validation_log
            }, f, indent=4)

if __name__ == "__main__":
    # Get base directory from environment
    base_dir = os.getenv("NOVA_BASE_DIR")
    if not base_dir:
        print("Error: NOVA_BASE_DIR environment variable not set")
        exit(1)
    
    # Initialize directory manager
    manager = DirectoryManager(base_dir)
    
    # Validate structure
    print("\n🔍 Validating directory structure...")
    if manager.validate_structure():
        print("✅ All directories valid")
    else:
        print("❌ Some directories invalid")
    
    # Create missing directories
    print("\n📁 Creating missing directories...")
    if manager.create_structure():
        print("✅ All directories created")
    else:
        print("❌ Some directories could not be created")
    
    # Save validation report
    report_file = Path(os.getenv("NOVA_PROCESSING_DIR", "")) / "directory_validation.json"
    manager.save_validation_report(report_file)
    print(f"\n📝 Validation report saved to: {report_file}") 