"""Error handling utilities for Nova document processor."""

from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import traceback

from ..errors import ValidationError, ComponentError
from ..logging import get_logger

logger = get_logger(__name__)

class ErrorHandler:
    """Component error handler with fallback mechanisms."""
    
    def __init__(self):
        """Initialize error handler."""
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.fallback_attempts: Dict[str, int] = {}
        self.max_retries = 3
        
    def handle_component_error(
        self,
        component_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        fallback_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Handle component error with fallback options.
        
        Args:
            component_name: Name of the component that failed
            error: The exception that occurred
            context: Optional context about the error
            fallback_config: Optional fallback configuration
            
        Returns:
            Tuple of (success, fallback_result)
            - success: Whether error was handled or fallback succeeded
            - fallback_result: Optional result from fallback mechanism
        """
        # Record error
        error_info = {
            'component': component_name,
            'error': str(error),
            'type': type(error).__name__,
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        self.errors.append(error_info)
        
        # Log error
        logger.error(
            f"Component error in {component_name}: {str(error)}",
            extra={'error_info': error_info}
        )
        
        # Check if we should try fallback
        if not fallback_config:
            return False, None
            
        # Check retry count
        retry_count = self.fallback_attempts.get(component_name, 0)
        if retry_count >= self.max_retries:
            logger.warning(
                f"Max retries ({self.max_retries}) reached for {component_name}"
            )
            return False, None
            
        # Attempt fallback
        try:
            logger.info(f"Attempting fallback for {component_name}")
            self.fallback_attempts[component_name] = retry_count + 1
            
            # Apply fallback configuration
            result = self._apply_fallback(component_name, fallback_config)
            
            # Record warning about using fallback
            self.warnings.append({
                'component': component_name,
                'message': f"Using fallback configuration (attempt {retry_count + 1})",
                'fallback_config': fallback_config
            })
            
            return True, result
            
        except Exception as e:
            logger.error(f"Fallback failed for {component_name}: {str(e)}")
            return False, None
            
    def handle_missing_key(
        self,
        component_name: str,
        key: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Handle missing component key with default value.
        
        Args:
            component_name: Name of the component
            key: Missing key
            context: Optional context about the missing key
            
        Returns:
            Optional default value for the key
        """
        # Get default value based on component type and key
        default_value = self._get_default_value(component_name, key)
        
        if default_value is not None:
            # Record warning about using default
            self.warnings.append({
                'component': component_name,
                'message': f"Using default value for missing key: {key}",
                'default_value': default_value,
                'context': context or {}
            })
            
            logger.warning(
                f"Using default value for missing key {key} in {component_name}",
                extra={'default_value': default_value}
            )
            
            return default_value
            
        # No default available
        error_info = {
            'component': component_name,
            'message': f"Missing required key: {key}",
            'context': context or {}
        }
        self.errors.append(error_info)
        
        logger.error(
            f"Missing required key {key} in {component_name}",
            extra={'error_info': error_info}
        )
        
        return None
        
    def _apply_fallback(
        self,
        component_name: str,
        fallback_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply fallback configuration for component.
        
        Args:
            component_name: Name of the component
            fallback_config: Fallback configuration to apply
            
        Returns:
            Applied fallback configuration
            
        Raises:
            ComponentError: If fallback cannot be applied
        """
        # Validate fallback config
        if not isinstance(fallback_config, dict):
            raise ComponentError(f"Invalid fallback config for {component_name}")
            
        # Apply component-specific fallback logic
        if component_name == 'markdown_processor':
            return self._fallback_markdown_processor(fallback_config)
        elif component_name == 'image_processor':
            return self._fallback_image_processor(fallback_config)
        elif component_name == 'office_processor':
            return self._fallback_office_processor(fallback_config)
        else:
            raise ComponentError(f"No fallback logic for {component_name}")
            
    def _fallback_markdown_processor(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback for markdown processor.
        
        Args:
            config: Fallback configuration
            
        Returns:
            Applied configuration
        """
        return {
            'parser': config.get('parser', 'markitdown==0.0.1a3'),
            'config': {
                'document_conversion': config.get('document_conversion', True),
                'image_processing': config.get('image_processing', False),
                'metadata_preservation': config.get('metadata_preservation', True)
            },
            'handlers': [{
                'base_handler': 'nova.phases.core.base_handler.BaseHandler'
            }]
        }
        
    def _fallback_image_processor(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback for image processor.
        
        Args:
            config: Fallback configuration
            
        Returns:
            Applied configuration
        """
        return {
            'formats': config.get('formats', ['png', 'jpg/jpeg']),
            'operations': [
                {
                    'format_conversion': {
                        'heic_to_jpg': True,
                        'optimize_quality': 85
                    }
                }
            ],
            'temp_files': {
                'use_stable_names': True,
                'cleanup_after_processing': True,
                'preserve_originals': True
            }
        }
        
    def _fallback_office_processor(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback for office processor.
        
        Args:
            config: Fallback configuration
            
        Returns:
            Applied configuration
        """
        return {
            'formats': {
                'docx/doc': {
                    'extract_text': True,
                    'preserve_paragraphs': True
                },
                'pdf': {
                    'extract_text': True,
                    'preserve_layout': True
                }
            },
            'operations': [
                {
                    'text_extraction': {
                        'preserve_formatting': True,
                        'handle_unicode': True
                    }
                }
            ],
            'content_extraction': {
                'try_attributes': ['text_content', 'markdown', 'text'],
                'fallback_to_dict': True,
                'log_failures': True
            }
        }
        
    def _get_default_value(self, component_name: str, key: str) -> Optional[Any]:
        """Get default value for component key.
        
        Args:
            component_name: Name of the component
            key: Configuration key
            
        Returns:
            Optional default value
        """
        defaults = {
            'markdown_processor': {
                'parser': 'markitdown==0.0.1a3',
                'document_conversion': True,
                'image_processing': False,
                'metadata_preservation': True
            },
            'image_processor': {
                'formats': ['png', 'jpg/jpeg'],
                'optimize_quality': 85,
                'max_dimensions': [1920, 1080],
                'preserve_aspect_ratio': True
            },
            'office_processor': {
                'extract_text': True,
                'preserve_paragraphs': True,
                'preserve_layout': True,
                'handle_unicode': True
            }
        }
        
        component_defaults = defaults.get(component_name, {})
        return component_defaults.get(key)
        
    def get_error_report(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed error report.
        
        Returns:
            Dictionary containing errors and warnings
        """
        return {
            'errors': self.errors,
            'warnings': self.warnings
        } 