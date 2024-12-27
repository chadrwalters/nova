"""Processor configuration management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .pipeline_config import PhaseConfig


@dataclass
class HandlerConfig:
    """Configuration for a processor handler."""
    type: str
    base_handler: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ComponentConfig:
    """Configuration for a processor component."""
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    handlers: List[HandlerConfig] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ProcessorConfig:
    """Configuration for a document processor."""
    name: str
    description: str
    output_dir: Path
    processor: Type[Any]
    components: Dict[str, ComponentConfig] = field(default_factory=dict)
    handlers: List[HandlerConfig] = field(default_factory=list)
    enabled: bool = True
    
    @classmethod
    def from_phase_config(cls, phase_config: PhaseConfig) -> 'ProcessorConfig':
        """Create processor configuration from phase configuration.
        
        Args:
            phase_config: Phase configuration
            
        Returns:
            Processor configuration instance
        """
        # Convert component dictionaries to ComponentConfig objects
        components = {}
        for name, comp_dict in phase_config.components.items():
            handlers = []
            for handler_dict in comp_dict.get("handlers", []):
                handlers.append(HandlerConfig(
                    type=handler_dict["type"],
                    base_handler=handler_dict["base_handler"],
                    config=handler_dict.get("config", {}),
                    enabled=handler_dict.get("enabled", True)
                ))
                
            components[name] = ComponentConfig(
                type=comp_dict["type"],
                config=comp_dict.get("config", {}),
                handlers=handlers,
                enabled=comp_dict.get("enabled", True)
            )
            
        return cls(
            name=phase_config.name,
            description=phase_config.description,
            output_dir=phase_config.output_dir,
            processor=phase_config.processor,
            components=components,
            enabled=phase_config.enabled
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "output_dir": str(self.output_dir),
            "processor": self.processor,
            "components": {
                name: {
                    "type": component.type,
                    "config": component.config,
                    "handlers": [
                        {
                            "type": handler.type,
                            "base_handler": handler.base_handler,
                            "config": handler.config,
                            "enabled": handler.enabled
                        }
                        for handler in component.handlers
                    ],
                    "enabled": component.enabled
                }
                for name, component in self.components.items()
            },
            "handlers": [
                {
                    "type": handler.type,
                    "base_handler": handler.base_handler,
                    "config": handler.config,
                    "enabled": handler.enabled
                }
                for handler in self.handlers
            ],
            "enabled": self.enabled
        }
        
    def get_component_config(self, component_name: str) -> Optional[ComponentConfig]:
        """Get configuration for a specific component.
        
        Args:
            component_name: Name of component
            
        Returns:
            Component configuration if found, None otherwise
        """
        return self.components.get(component_name)
        
    def get_enabled_components(self) -> Dict[str, ComponentConfig]:
        """Get dictionary of enabled components.
        
        Returns:
            Dictionary mapping component names to configurations
        """
        return {
            name: component
            for name, component in self.components.items()
            if component.enabled
        }
        
    def get_enabled_handlers(self) -> List[HandlerConfig]:
        """Get list of enabled handlers.
        
        Returns:
            List of enabled handler configurations
        """
        return [handler for handler in self.handlers if handler.enabled]
        
    def validate(self) -> None:
        """Validate processor configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate basic fields
        if not self.name:
            raise ValueError("No processor name configured")
            
        if not self.processor:
            raise ValueError("No processor class configured")
            
        if not self.output_dir:
            raise ValueError("No output directory configured")
            
        # Validate components
        component_names = set()
        for name, component in self.components.items():
            if name in component_names:
                raise ValueError(f"Duplicate component name: {name}")
            component_names.add(name)
            
            # Validate component configuration
            if not component.type:
                raise ValueError(f"No type configured for component {name}")
                
            # Validate component handlers
            handler_types = set()
            for handler in component.handlers:
                if not handler.type:
                    raise ValueError(f"No type configured for handler in component {name}")
                    
                if not handler.base_handler:
                    raise ValueError(f"No base handler configured for handler {handler.type} in component {name}")
                    
                if handler.type in handler_types:
                    raise ValueError(f"Duplicate handler type {handler.type} in component {name}")
                handler_types.add(handler.type)
                
        # Validate processor handlers
        handler_types = set()
        for handler in self.handlers:
            if not handler.type:
                raise ValueError("No type configured for processor handler")
                
            if not handler.base_handler:
                raise ValueError(f"No base handler configured for handler {handler.type}")
                
            if handler.type in handler_types:
                raise ValueError(f"Duplicate handler type {handler.type}")
            handler_types.add(handler.type) 