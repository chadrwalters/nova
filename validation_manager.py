#!/usr/bin/env python3

import os
import sys
import json
import chardet
import markdown
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import importlib.util
from datetime import datetime

class ValidationManager:
    """Manages validation checks for the Nova pipeline."""
    
    def __init__(self, base_dir: Union[str, Path]):
        """Initialize the validation manager.
        
        Args:
            base_dir: Base directory path containing input/processing dirs
        """
        self.base_dir = Path(base_dir)
        self.validation_log = []
        self._load_environment()

    def _load_environment(self) -> None:
        """Load and validate environment variables."""
        required_vars = [
            "NOVA_INPUT_DIR",
            "NOVA_OUTPUT_DIR",
            "NOVA_PROCESSING_DIR",
            "NOVA_TEMP_DIR",
            "NOVA_PHASE_MARKDOWN_PARSE",
            "NOVA_PHASE_MARKDOWN_CONSOLIDATE",
            "NOVA_PHASE_MARKDOWN_AGGREGATE",
            "NOVA_PHASE_MARKDOWN_SPLIT",
            "NOVA_ORIGINAL_IMAGES_DIR",
            "NOVA_PROCESSED_IMAGES_DIR",
            "NOVA_IMAGE_METADATA_DIR",
            "NOVA_IMAGE_CACHE_DIR",
            "NOVA_OFFICE_ASSETS_DIR",
            "NOVA_OFFICE_TEMP_DIR"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _log_validation(self, check: str, status: bool, message: str) -> None:
        """Log a validation check result.
        
        Args:
            check: Name of the check
            status: True if passed, False if failed
            message: Description or error message
        """
        self.validation_log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "check": check,
            "status": "passed" if status else "failed",
            "message": message
        })

    def check_directory_permissions(self) -> bool:
        """Check if all required directories exist and are writable."""
        required_dirs = [
            os.getenv("NOVA_INPUT_DIR"),
            os.getenv("NOVA_OUTPUT_DIR"),
            os.getenv("NOVA_PROCESSING_DIR"),
            os.getenv("NOVA_TEMP_DIR"),
            os.getenv("NOVA_PHASE_MARKDOWN_PARSE"),
            os.getenv("NOVA_PHASE_MARKDOWN_CONSOLIDATE"),
            os.getenv("NOVA_PHASE_MARKDOWN_AGGREGATE"),
            os.getenv("NOVA_PHASE_MARKDOWN_SPLIT"),
            os.getenv("NOVA_ORIGINAL_IMAGES_DIR"),
            os.getenv("NOVA_PROCESSED_IMAGES_DIR"),
            os.getenv("NOVA_IMAGE_METADATA_DIR"),
            os.getenv("NOVA_IMAGE_CACHE_DIR"),
            os.getenv("NOVA_OFFICE_ASSETS_DIR"),
            os.getenv("NOVA_OFFICE_TEMP_DIR")
        ]
        
        all_valid = True
        for dir_path in required_dirs:
            if dir_path is None:
                continue
                
            path = Path(dir_path)
            if not path.exists():
                self._log_validation("directory_exists", False, f"Directory does not exist: {path}")
                all_valid = False
                continue
                
            if not os.access(path, os.W_OK):
                self._log_validation("directory_permissions", False, f"Directory not writable: {path}")
                all_valid = False
                continue
                
            self._log_validation("directory_check", True, f"Directory valid: {path}")
            
        return all_valid

    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed."""
        required_packages = [
            ("markdown", "markdown"),
            ("chardet", "chardet"),
            ("python-magic", "magic"),
            ("Pillow", "PIL"),
            ("python-docx", "docx"),
            ("openpyxl", "openpyxl"),
            ("PyPDF2", "PyPDF2")
        ]
        
        all_valid = True
        for package_name, import_name in required_packages:
            try:
                spec = importlib.util.find_spec(import_name)
                if spec is None:
                    self._log_validation("dependency_check", False, f"Package not found: {package_name}")
                    all_valid = False
                else:
                    self._log_validation("dependency_check", True, f"Package found: {package_name}")
            except ImportError:
                self._log_validation("dependency_check", False, f"Package import failed: {package_name}")
                all_valid = False
                
        return all_valid

    def validate_input_files(self) -> Tuple[bool, List[Path]]:
        """Validate input markdown files.
        
        Returns:
            Tuple[bool, List[Path]]: (success status, list of valid files)
        """
        input_dir = Path(os.getenv("NOVA_INPUT_DIR", ""))
        if not input_dir.exists():
            self._log_validation("input_directory", False, f"Input directory not found: {input_dir}")
            return False, []
            
        markdown_files = list(input_dir.glob("**/*.md"))
        if not markdown_files:
            self._log_validation("input_files", False, "No markdown files found in input directory")
            return False, []
            
        valid_files = []
        for file_path in markdown_files:
            # Check file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                self._log_validation("file_access", False, f"File not accessible: {file_path}")
                continue
                
            # Check file encoding
            try:
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                    result = chardet.detect(raw_content)
                    if result['encoding'] not in ['utf-8', 'ascii']:
                        self._log_validation("file_encoding", False, 
                            f"Invalid encoding for {file_path}: {result['encoding']}")
                        continue
            except Exception as e:
                self._log_validation("file_encoding", False, 
                    f"Error checking encoding for {file_path}: {str(e)}")
                continue
                
            # Check markdown syntax
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    markdown.markdown(content)
                self._log_validation("markdown_syntax", True, f"Valid markdown: {file_path}")
                valid_files.append(file_path)
            except Exception as e:
                self._log_validation("markdown_syntax", False, 
                    f"Invalid markdown in {file_path}: {str(e)}")
                continue
                
        return len(valid_files) > 0, valid_files

    def save_validation_report(self) -> None:
        """Save the validation log to a report file."""
        report_file = Path(os.getenv("NOVA_PROCESSING_DIR", "")) / "validation_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "validation_log": self.validation_log
            }, f, indent=4)

    def run_all_checks(self) -> Tuple[bool, Dict]:
        """Run all validation checks.
        
        Returns:
            Tuple[bool, Dict]: (overall success status, validation results)
        """
        results = {
            "directory_permissions": self.check_directory_permissions(),
            "dependencies": self.check_dependencies(),
            "input_files": self.validate_input_files()[0]
        }
        
        overall_success = all(results.values())
        self.save_validation_report()
        
        return overall_success, results

if __name__ == "__main__":
    # Get base directory from environment
    base_dir = os.getenv("NOVA_BASE_DIR")
    if not base_dir:
        print("Error: NOVA_BASE_DIR environment variable not set")
        sys.exit(1)
        
    # Run validation
    validator = ValidationManager(base_dir)
    success, results = validator.run_all_checks()
    
    # Print results
    print("\n🔍 Validation Results:")
    for check, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check}: {'Passed' if status else 'Failed'}")
    
    print(f"\n📝 Detailed report saved to: {os.getenv('NOVA_PROCESSING_DIR')}/validation_report.json")
    
    if not success:
        print("\n❌ Validation failed. Please check the report for details.")
        sys.exit(1)
    else:
        print("\n✅ All validation checks passed!") 