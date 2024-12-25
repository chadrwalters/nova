"""Configuration module for Nova document processor.

This module handles loading and managing configuration for the Nova pipeline.
The configuration is split between two files:
1. default_config.yaml: Global system configuration
2. pipeline_config.yaml: Pipeline-specific configuration

For more details, see docs/configuration.md
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from pydantic import BaseModel, Field

from .base import PipelineConfig, ProcessorConfig, ComponentConfig
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
        
    # Handle phases
    if 'phases' in pipeline:
        phases = pipeline['phases']
        if isinstance(phases, list):
            # Convert list of dicts to list of strings
            phase_names = []
            phase_configs = {}
            for phase in phases:
                if isinstance(phase, dict):
                    for name, config in phase.items():
                        phase_names.append(name)
                        phase_configs[name] = config
                else:
                    phase_names.append(phase)
            pipeline['phases'] = phase_names
            pipeline['phase_configs'] = phase_configs
        
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
                    
            new_components[name] = component
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
    return PipelineConfig(**pipeline_data)
