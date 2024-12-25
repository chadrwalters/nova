"""Configuration module for Nova document processor.

This module handles loading and managing configuration for the Nova pipeline.
The configuration is split between two files:
1. default_config.yaml: Global system configuration
2. pipeline_config.yaml: Pipeline-specific configuration

For more details, see docs/configuration.md
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml
from pydantic import BaseModel, Field

from .base import PipelineConfig, ProcessorConfig, ComponentConfig, HandlerConfig, PathConfig
from ..logging import get_logger

logger = get_logger(__name__)

def _transform_components(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform components configuration.
    
    Args:
        config_data: Raw configuration data
        
    Returns:
        Transformed configuration data
    """
    if 'pipeline' not in config_data:
        config_data['pipeline'] = {}
        
    pipeline = config_data.get('pipeline', {})
    
    # Handle paths
    if 'paths' not in pipeline:
        pipeline['paths'] = {'base_dir': os.getenv('NOVA_BASE_DIR')}
    paths = pipeline['paths']
    if isinstance(paths, dict):
        pipeline['paths'] = PathConfig(**paths)
    
    def _transform_handlers(handlers: Any) -> List[HandlerConfig]:
        """Transform handlers to list of HandlerConfig objects."""
        if isinstance(handlers, dict):
            # Convert dict format to list format
            handler_list = []
            for handler_name, handler_config in handlers.items():
                if isinstance(handler_config, dict):
                    # Add handler name as type if not present
                    if 'type' not in handler_config:
                        handler_config['type'] = handler_name
                    handler_list.append(HandlerConfig(**handler_config))
            return handler_list
        elif isinstance(handlers, list):
            # Already in list format
            handler_list = []
            for handler in handlers:
                if isinstance(handler, dict):
                    if 'type' not in handler:
                        handler['type'] = 'UnifiedHandler'
                    handler_list.append(HandlerConfig(**handler))
            return handler_list
        return []
    
    # Handle phases
    if 'phases' in pipeline:
        phases = pipeline['phases']
        if isinstance(phases, list):
            # Convert list of dicts to list of ProcessorConfig objects
            phase_configs = []
            for phase in phases:
                if isinstance(phase, dict):
                    for name, config in phase.items():
                        # Add phase name to config
                        config['name'] = name
                        
                        # Add processor name if not present
                        if 'processor' not in config:
                            config['processor'] = name.replace('_', '') + 'Processor'
                        
                        # Add description if not present
                        if 'description' not in config:
                            config['description'] = f"Process {name.lower().replace('_', ' ')}"
                        
                        # Convert handlers to HandlerConfig objects
                        if 'handlers' in config:
                            config['handlers'] = _transform_handlers(config['handlers'])
                        
                        # Convert components to ComponentConfig objects
                        if 'components' in config:
                            components = config['components']
                            if isinstance(components, dict):
                                for comp_name, comp_config in components.items():
                                    if 'handlers' in comp_config:
                                        comp_config['handlers'] = _transform_handlers(comp_config['handlers'])
                                config['components'] = {
                                    name: ComponentConfig(**component)
                                    for name, component in components.items()
                                }
                        else:
                            # Initialize empty components dictionary
                            config['components'] = {}
                        
                        # Create ProcessorConfig
                        try:
                            logger.debug(f"Creating processor config for {name}: {config}")
                            phase_configs.append(ProcessorConfig(
                                name=name,
                                description=config.get('description', f"Process {name.lower().replace('_', ' ')}"),
                                output_dir=config['output_dir'],
                                processor=config.get('processor', name.replace('_', '') + 'Processor'),
                                enabled=config.get('enabled', True),
                                components=config.get('components', {}),
                                handlers=config.get('handlers', [])
                            ))
                        except Exception as e:
                            logger.error(f"Failed to create processor config for {name}: {e}")
                            logger.debug(f"Config data: {config}")
                            raise
            pipeline['phases'] = phase_configs
        
    # Handle components
    if 'components' not in pipeline:
        pipeline['components'] = {}
        
    components = pipeline['components']
    if not isinstance(components, dict):
        pipeline['components'] = {}
        return config_data
    
    # Transform each component
    for name, component in components.items():
        if not isinstance(component, dict):
            continue
            
        # Convert handlers to HandlerConfig objects
        if 'handlers' in component:
            component['handlers'] = _transform_handlers(component['handlers'])
            
        # Convert formats list to dict if needed
        if 'formats' in component and isinstance(component['formats'], list):
            formats = component['formats']
            if all(isinstance(f, dict) for f in formats):
                new_formats = {}
                for fmt in formats:
                    for k, v in fmt.items():
                        new_formats[k] = v
                component['formats'] = new_formats
                
    # Create ComponentConfig objects
    new_components = {}
    for name, component in components.items():
        if isinstance(component, dict):
            # Convert formats to list of strings if they are simple strings
            if 'formats' in component and isinstance(component['formats'], list):
                formats = component['formats']
                if all(isinstance(f, str) for f in formats):
                    component['formats'] = formats
                    
            new_components[name] = ComponentConfig(**component)
        else:
            new_components[name] = component
            
    pipeline['components'] = new_components
    config_data['pipeline'] = pipeline
                
    return config_data

def load_config(config_path: Optional[str] = None) -> PipelineConfig:
    """Load pipeline configuration.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Pipeline configuration
        
    Raises:
        FileNotFoundError: If config file not found
    """
    if not config_path:
        # Get the path to the nova package directory
        nova_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        # Config file is in the config directory at the root of the project
        config_path = os.path.join(os.path.dirname(nova_dir), 'config', 'pipeline_config.yaml')
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
        
    # Transform components before creating config
    config_data = _transform_components(config_data)
    
    # Extract pipeline configuration
    pipeline_data = config_data.get('pipeline', {})
    
    # Create PipelineConfig
    try:
        logger.debug(f"Creating pipeline config with data: {pipeline_data}")
        return PipelineConfig(**pipeline_data)
    except Exception as e:
        logger.error(f"Failed to create pipeline config: {e}")
        logger.debug(f"Pipeline data: {pipeline_data}")
        raise
