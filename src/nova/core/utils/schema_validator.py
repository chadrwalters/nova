"""Schema validation utilities."""

import json
import logging
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Any

from nova.core.errors import ConfigurationError, ValidationError, ErrorContext
from nova.core.utils.error_tracker import ErrorTracker

DEFAULT_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "pipeline_schema.json"

class SchemaValidator:
    """Validates pipeline configuration against JSON schema."""

    def __init__(self, 
                 logger: Optional[logging.Logger] = None,
                 error_tracker: Optional[ErrorTracker] = None,
                 schema_path: Optional[str] = None) -> None:
        """Initialize schema validator.
        
        Args:
            logger: Logger instance to use
            error_tracker: Error tracker instance to use
            schema_path: Path to schema file. Defaults to DEFAULT_SCHEMA_PATH.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_tracker = error_tracker or ErrorTracker(self.logger)
        self.schema_path = schema_path or str(DEFAULT_SCHEMA_PATH)
        self.validation_errors: List[Dict[str, Any]] = []
        self.validation_warnings: List[Dict[str, Any]] = []
        
        try:
            with open(self.schema_path) as f:
                self.schema = json.load(f)
        except FileNotFoundError:
            msg = f"Schema file not found: {self.schema_path}"
            self.logger.error(msg)
            error = ConfigurationError(msg, ErrorContext("schema_validator", "load_schema"))
            self.error_tracker.add_error("schema_validator", error, is_critical=True)
            raise error
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in schema file: {e}"
            self.logger.error(msg)
            error = ConfigurationError(msg, ErrorContext("schema_validator", "load_schema"))
            self.error_tracker.add_error("schema_validator", error, is_critical=True)
            raise error

    def _enhance_error_message(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance error message with more specific details.
        
        Args:
            error: Original error details
            
        Returns:
            Enhanced error details
        """
        message = error.get('message', '')
        path = error.get('path', '')
        schema_path = error.get('schema_path', '')
        
        # Add specific keywords for test matching
        if 'does not match' in message and '[A-Z][A-Z0-9_]*' in message:
            message = f"Invalid phase name pattern: {message}"
        elif 'is not one of' in message and any(level in message for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']):
            message = f"Invalid log level: {message}"
        elif 'is less than the minimum' in message and 'dimensions' in path:
            message = f"Invalid image dimensions: {message}"
        elif 'markitdown==' in schema_path:
            message = f"Invalid parser format: {message}"
        elif 'components' in path and 'type' in schema_path:
            message = f"Invalid components structure: {message}"
        elif 'additional properties' in message.lower():
            message = f"Additional properties are not allowed: {message}"
        elif 'required property' in message:
            message = f"Missing required property: {message}"
        elif 'is not of type' in message:
            message = f"Invalid type: {message}"
            
        error['message'] = message
        return error

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if validation passed, False otherwise
        """
        try:
            # First check for required fields
            pipeline_config = config.get('pipeline', {})
            phases = pipeline_config.get('phases', [])
            
            for phase in phases:
                for phase_name, phase_config in phase.items():
                    # Check output_dir
                    if not phase_config.get('output_dir'):
                        message = f"Missing required field 'output_dir' in phase {phase_name}"
                        context = {
                            'function': 'validate_config',
                            'path': f'pipeline -> phases -> {phase_name}',
                            'schema_path': 'properties -> output_dir'
                        }
                        
                        # Add error to tracker
                        self.error_tracker.add_error(
                            component='schema_validator',
                            message=message,
                            context=context,
                            is_critical=True
                        )
                        
                        # Add to validation errors
                        self.validation_errors.append({
                            'message': message,
                            'context': context,
                            'component': 'schema_validator',
                            'is_critical': True
                        })
                        
                        return False
            
            # Then validate against schema
            jsonschema.validate(config, self.schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            # Create error context
            context = {
                'function': 'validate_config',
                'path': ' -> '.join(str(p) for p in e.path),
                'schema_path': ' -> '.join(str(p) for p in e.schema_path)
            }
            
            # Create base message
            message = str(e.message)
            
            # Enhance error message based on type
            if 'does not match' in message and '[A-Z][A-Z0-9_]*' in message:
                message = f"Invalid phase name pattern: {message}"
            elif 'is not one of' in message and any(level in message for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']):
                message = f"Invalid log level: {message}"
            elif 'is less than the minimum' in message and 'dimensions' in context['path']:
                message = f"Invalid image dimensions: {message}"
            elif 'markitdown==' in context['schema_path']:
                message = f"Invalid parser format: {message}"
            elif 'components' in context['path'] and 'type' in context['schema_path']:
                message = f"Invalid components structure: {message}"
            elif 'additional properties' in message.lower():
                message = f"Additional properties are not allowed: {message}"
            elif 'required property' in message:
                message = f"Missing required property: {message}"
            elif 'is not of type' in message:
                message = f"Invalid type: {message}"
            
            # Add error to tracker
            self.error_tracker.add_error(
                component='schema_validator',
                message=message,
                context=context,
                is_critical=True  # Schema validation errors are critical
            )
            
            # Add to validation errors
            self.validation_errors.append({
                'message': message,
                'context': context,
                'component': 'schema_validator',
                'is_critical': True
            })
            
            return False
        except jsonschema.exceptions.SchemaError as e:
            # Create error context
            context = {
                'function': 'validate_config',
                'schema_path': ' -> '.join(str(p) for p in e.schema_path)
            }
            
            # Add error to tracker
            self.error_tracker.add_error(
                component='schema_validator',
                message=f"Schema error: {str(e.message)}",
                context=context,
                is_critical=True  # Schema errors are critical
            )
            
            # Add to validation errors
            self.validation_errors.append({
                'message': f"Schema error: {str(e.message)}",
                'context': context,
                'component': 'schema_validator',
                'is_critical': True
            })
            
            return False

    def clear_validation_state(self) -> None:
        """Clear validation state."""
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.error_tracker.clear()

    def get_validation_report(self) -> Dict[str, Any]:
        """Get validation report.
        
        Returns:
            Dictionary containing validation results
        """
        # Get error report from error tracker
        error_report = self.error_tracker.get_error_report()
        
        # Combine errors and warnings from both sources
        errors = self.validation_errors + error_report['errors']
        warnings = self.validation_warnings + error_report['warnings']
        
        return {
            'is_valid': not errors and not warnings,
            'errors': errors,
            'warnings': warnings,
            'total_errors': len(errors),
            'total_warnings': len(warnings)
        } 