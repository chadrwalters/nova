"""YAML validation utilities for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import yaml

from ..errors import ValidationError
from ..logging import get_logger
from .validation import validate_path

logger = get_logger(__name__)

class YAMLValidator:
    """YAML configuration validator."""
    
    def __init__(self):
        """Initialize validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """Validate YAML file structure and content.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            bool: True if valid, False if invalid
        """
        try:
            # Validate path
            path = validate_path(file_path, must_exist=True, must_be_file=True)
            
            # Load YAML
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            return self.validate_config(config)
            
        except Exception as e:
            self.errors.append(f"Failed to validate {file_path}: {str(e)}")
            return False
            
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if valid, False if invalid
        """
        is_valid = True
        
        # Check pipeline section
        if 'pipeline' not in config:
            self.errors.append("Missing required 'pipeline' section")
            return False
            
        pipeline = config['pipeline']
        
        # Check phases section
        if 'phases' not in pipeline:
            self.errors.append("Missing required 'phases' section in pipeline")
            return False
            
        phases = pipeline['phases']
        if not isinstance(phases, list):
            self.errors.append("'phases' must be a list")
            return False
            
        # Validate each phase
        for phase in phases:
            if not self._validate_phase(phase):
                is_valid = False
                
        return is_valid
        
    def _validate_phase(self, phase: Dict[str, Any]) -> bool:
        """Validate a pipeline phase configuration.
        
        Args:
            phase: Phase configuration
            
        Returns:
            bool: True if valid, False if invalid
        """
        is_valid = True
        
        # Check required phase fields
        required_fields = {
            'description': str,
            'output_dir': str,
            'processor': str,
            'components': (dict, list)  # Allow both dict and list formats
        }
        
        for field, expected_type in required_fields.items():
            if field not in phase:
                self.errors.append(f"Missing required field '{field}' in phase")
                is_valid = False
                continue
                
            value = phase[field]
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = ' or '.join(t.__name__ for t in expected_type)
                    self.errors.append(
                        f"Field '{field}' must be {type_names}, got {type(value).__name__}"
                    )
                else:
                    self.errors.append(
                        f"Field '{field}' must be {expected_type.__name__}, got {type(value).__name__}"
                    )
                is_valid = False
                
        # Validate components structure
        if is_valid and 'components' in phase:
            components = phase['components']
            
            # Check if using list format
            if isinstance(components, list):
                self.warnings.append(
                    "Using list format for components. Dictionary format is recommended."
                )
                # Validate each component in list
                for component in components:
                    if not isinstance(component, dict):
                        self.errors.append("Each component must be a dictionary")
                        is_valid = False
                        continue
                    if not self._validate_component(component):
                        is_valid = False
                        
            # Check if using dict format
            elif isinstance(components, dict):
                # Validate each component in dict
                for name, component in components.items():
                    if not isinstance(component, dict):
                        self.errors.append(f"Component '{name}' must be a dictionary")
                        is_valid = False
                        continue
                    if not self._validate_component({name: component}):
                        is_valid = False
                        
        return is_valid
        
    def _validate_component(self, component: Dict[str, Any]) -> bool:
        """Validate a component configuration.
        
        Args:
            component: Component configuration
            
        Returns:
            bool: True if valid, False if invalid
        """
        is_valid = True
        
        # Get component name and config
        if len(component) != 1:
            self.errors.append("Each component must have exactly one top-level key")
            return False
            
        name = list(component.keys())[0]
        config = component[name]
        
        # Validate component config
        if not isinstance(config, dict):
            self.errors.append(f"Component '{name}' configuration must be a dictionary")
            return False
            
        # Check for required sections based on component type
        if name == 'markdown_processor':
            required = {'parser', 'config', 'handlers'}
        elif name == 'image_processor':
            required = {'formats', 'operations', 'temp_files'}
        elif name == 'office_processor':
            required = {'formats', 'operations', 'content_extraction'}
        else:
            self.warnings.append(f"Unknown component type: {name}")
            return True
            
        # Check required sections
        for section in required:
            if section not in config:
                self.errors.append(f"Missing required section '{section}' in {name}")
                is_valid = False
                
        return is_valid
        
    def get_validation_report(self) -> Dict[str, List[str]]:
        """Get validation results.
        
        Returns:
            Dictionary containing errors and warnings
        """
        return {
            'errors': self.errors,
            'warnings': self.warnings
        } 