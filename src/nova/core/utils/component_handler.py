"""Component handler module for managing pipeline components."""

import logging
from typing import Any, Dict, List, Optional, Type, Union
import asyncio
import re

from nova.core.errors import (
    ComponentError,
    ConfigurationError,
    ErrorContext,
    ValidationError
)

class ComponentHandler:
    """Handles pipeline component configuration and validation."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize component handler.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.warnings = []
        self._components = {}
        
    def clear_components(self) -> None:
        """Clear all component configurations."""
        self._components.clear()
        self.warnings.clear()
        
    async def apply_component_config(self, component_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply and validate component configuration."""
        self.warnings = []  # Reset warnings for each validation
        
        if not isinstance(config, dict):
            raise ComponentError(f"Configuration for {component_type} must be a dictionary")
            
        # Validate component type first
        if component_type not in {"markdown_processor", "image_processor", "office_processor"}:
            raise ComponentError(
                f"Unknown component type: {component_type}",
                context=ErrorContext(
                    component=component_type,
                    operation='validate_config'
                )
            )
            
        # Apply component-specific validation and defaults
        if component_type == "markdown_processor":
            config = await self._apply_markdown_config(config)
        elif component_type == "image_processor":
            config = await self._apply_image_config(config)
        elif component_type == "office_processor":
            config = await self._apply_office_config(config)
            
        # Validate final configuration
        self._validate_component_config(component_type, config)
            
        return config
        
    async def _apply_markdown_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply markdown processor configuration."""
        # Check for required fields
        if "parser" not in config:
            raise ConfigurationError("Missing required field: parser")
            
        # Check for recommended fields
        if "config" in config:
            if not isinstance(config["config"], dict):
                raise ConfigurationError("'config' field must be a dictionary")
                
            for key in ["document_conversion", "image_processing", "metadata_preservation"]:
                if key not in config["config"]:
                    self.warnings.append({
                        "message": f"Using default value for {key}",
                        "component": "markdown_processor",
                        "details": {"field": key},
                        "is_critical": False
                    })
                    config["config"][key] = True
        else:
            # If config is not present, create it with default values
            config["config"] = {
                "document_conversion": True,
                "image_processing": True,
                "metadata_preservation": True
            }
            self.warnings.append({
                "message": "Using default configuration",
                "component": "markdown_processor",
                "details": {"config": config["config"]},
                "is_critical": False
            })
                    
        # Validate parser version format if present
        if "parser" in config and not re.match(r"^markitdown==\d+\.\d+\.\d+[a-z]\d+$", config["parser"]):
            self.warnings.append({
                "message": "Non-standard parser version specified",
                "component": "markdown_processor",
                "details": {"parser": config["parser"]},
                "is_critical": False
            })
            
        # Validate handlers if present
        if "handlers" in config:
            if not isinstance(config["handlers"], list):
                raise ConfigurationError("handlers must be list")
                
        return config
        
    async def _apply_image_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply image processor configuration."""
        # Check for required fields
        required_fields = {"formats", "operations", "temp_files"}
        missing_fields = required_fields - set(config.keys())
        if missing_fields:
            if "temp_files" in missing_fields:
                config["temp_files"] = {
                    "use_stable_names": True,
                    "cleanup_after_processing": True,
                    "preserve_originals": True
                }
                self.warnings.append({
                    "message": "Using default temp_files configuration",
                    "component": "image_processor",
                    "details": {"config": config["temp_files"]},
                    "is_critical": False
                })
            if len(missing_fields - {"temp_files"}) > 0:
                raise ConfigurationError(f"Missing required fields: {missing_fields - {'temp_files'}}")
                
        # Check for missing temp_files settings
        if "temp_files" in config:
            for key in ["use_stable_names", "cleanup_after_processing", "preserve_originals"]:
                if key not in config["temp_files"]:
                    self.warnings.append({
                        "message": f"Using default value for {key}",
                        "component": "image_processor",
                        "details": {"field": key},
                        "is_critical": False
                    })
                    config["temp_files"][key] = True
                    
        # Validate formats if present
        if "formats" in config:
            if not isinstance(config["formats"], list):
                raise ConfigurationError("formats must be list")
                
            valid_formats = {"png", "jpg/jpeg", "gif", "webp", "heic/HEIC"}
            for fmt in config["formats"]:
                if fmt not in valid_formats:
                    self.warnings.append({
                        "message": f"Unsupported format: {fmt}",
                        "component": "image_processor",
                        "details": {"format": fmt},
                        "is_critical": False
                    })
                    
        # Validate operations if present
        if "operations" in config:
            if not isinstance(config["operations"], list):
                raise ConfigurationError("operations must be list")
                
            for operation in config["operations"]:
                if not isinstance(operation, dict):
                    raise ConfigurationError("operation must be dictionary")
                    
                for op_name, op_config in operation.items():
                    if op_name == "size_optimization":
                        if "max_dimensions" in op_config:
                            dimensions = op_config["max_dimensions"]
                            if not isinstance(dimensions, list) or len(dimensions) != 2:
                                raise ConfigurationError("max_dimensions must be list of two integers")
                            if any(not isinstance(d, int) or d <= 0 for d in dimensions):
                                raise ConfigurationError("dimensions must be greater than 0")
                                
        return config
        
    async def _apply_office_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply office processor configuration."""
        # Check for required fields
        required_fields = {"formats", "operations", "content_extraction"}
        missing_fields = required_fields - set(config.keys())
        if missing_fields:
            if "content_extraction" in missing_fields:
                config["content_extraction"] = {
                    "try_attributes": ["text_content", "markdown", "text"],
                    "fallback_to_dict": True,
                    "log_failures": True
                }
                self.warnings.append({
                    "message": "Using default content_extraction configuration",
                    "component": "office_processor",
                    "details": {"config": config["content_extraction"]},
                    "is_critical": False
                })
            if len(missing_fields - {"content_extraction"}) > 0:
                raise ConfigurationError(f"Missing required fields: {missing_fields - {'content_extraction'}}")
                
        # Check for missing content_extraction settings
        if "content_extraction" in config:
            if "try_attributes" not in config["content_extraction"]:
                self.warnings.append({
                    "message": "Using default try_attributes",
                    "component": "office_processor",
                    "details": {"field": "try_attributes"},
                    "is_critical": False
                })
                config["content_extraction"]["try_attributes"] = ["text_content", "markdown", "text"]
                
            for key in ["fallback_to_dict", "log_failures"]:
                if key not in config["content_extraction"]:
                    self.warnings.append({
                        "message": f"Using default value for {key}",
                        "component": "office_processor",
                        "details": {"field": key},
                        "is_critical": False
                    })
                    config["content_extraction"][key] = True
                    
        # Validate formats if present
        if "formats" in config:
            if not isinstance(config["formats"], dict):
                raise ConfigurationError("formats must be dictionary")
                
            valid_formats = {"docx/doc", "pptx/ppt", "xlsx/xls", "pdf", "csv"}
            for fmt in config["formats"].keys():
                if fmt not in valid_formats:
                    self.warnings.append({
                        "message": f"Unsupported format: {fmt}",
                        "component": "office_processor",
                        "details": {"format": fmt},
                        "is_critical": False
                    })
                    
        return config
        
    def _validate_component_config(self, component_type: str, config: Dict[str, Any]) -> None:
        """Validate component configuration."""
        if component_type == "markdown_processor":
            if "parser" not in config:
                raise ConfigurationError("Missing required field: parser")
            if "handlers" in config and not isinstance(config["handlers"], list):
                raise ConfigurationError("handlers must be list")
                
        elif component_type == "image_processor":
            required_fields = {"formats", "operations", "temp_files"}
            missing_fields = required_fields - set(config.keys())
            if len(missing_fields - {"temp_files"}) > 0:
                raise ConfigurationError(f"Missing required fields: {missing_fields - {'temp_files'}}")
                
            if "formats" in config and not isinstance(config["formats"], list):
                raise ConfigurationError("formats must be list")
                
            if "operations" in config:
                if not isinstance(config["operations"], list):
                    raise ConfigurationError("operations must be list")
                    
                for operation in config["operations"]:
                    if not isinstance(operation, dict):
                        raise ConfigurationError("operation must be dictionary")
                        
                    for op_name, op_config in operation.items():
                        if op_name == "size_optimization":
                            if "max_dimensions" in op_config:
                                dimensions = op_config["max_dimensions"]
                                if not isinstance(dimensions, list) or len(dimensions) != 2:
                                    raise ConfigurationError("max_dimensions must be list of two integers")
                                if any(not isinstance(d, int) or d <= 0 for d in dimensions):
                                    raise ConfigurationError("dimensions must be greater than 0")
                                    
        elif component_type == "office_processor":
            required_fields = {"formats", "operations", "content_extraction"}
            missing_fields = required_fields - set(config.keys())
            if len(missing_fields - {"content_extraction"}) > 0:
                raise ConfigurationError(f"Missing required fields: {missing_fields - {'content_extraction'}}")
                
            if "formats" in config and not isinstance(config["formats"], dict):
                raise ConfigurationError("formats must be dictionary")
                
    def get_warnings(self) -> List[Dict[str, Any]]:
        """Get accumulated warnings."""
        return self.warnings 