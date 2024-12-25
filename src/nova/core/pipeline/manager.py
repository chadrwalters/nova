"""Pipeline manager module for Nova document processor."""

import logging
from typing import Any, Dict, List, Optional
import asyncio

from nova.core.utils.component_handler import ComponentHandler
from nova.core.utils.schema_validator import SchemaValidator
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.errors import (
    NovaError,
    ConfigurationError,
    ErrorContext,
    with_retry,
    handle_errors
)

class PipelineManager:
    """Manages pipeline configuration and execution."""
    
    def __init__(self, config: Any = None, logger: Optional[logging.Logger] = None, error_tracker: Optional[ErrorTracker] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.component_handler = ComponentHandler(logger)
        self.schema_validator = SchemaValidator(logger)
        self.error_tracker = error_tracker or ErrorTracker(logger)
        self._config = config
        self._components: Dict[str, Dict[str, Any]] = {}
    
    @property
    def config(self) -> Optional[Dict[str, Any]]:
        """Get current pipeline configuration."""
        return self._config
    
    def get_component_config(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get component configuration.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component configuration dictionary or None if not found
        """
        if not self._config:
            return None
        
        pipeline_config = self._config.get('pipeline', {})
        components = pipeline_config.get('components', {})
        return components.get(component_name)
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get validation report from schema validator."""
        # Get reports from both sources
        validator_report = self.schema_validator.get_validation_report()
        error_report = self.error_tracker.get_error_report()
        
        # Combine errors and warnings
        errors = validator_report['errors'] + error_report['errors']
        warnings = validator_report['warnings'] + error_report['warnings']
        
        return {
            'is_valid': not errors and not warnings,
            'errors': errors,
            'warnings': warnings,
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'components': list(set(error_report['components']))
        }
    
    def clear_state(self) -> None:
        """Clear pipeline manager state."""
        self._config = None
        self._components.clear()
        self.error_tracker.clear()
        self.schema_validator.clear_validation_state()
    
    def _validate_phase_dependencies(self, phases: List[Dict[str, Any]]) -> None:
        """Validate phase dependencies and output directories.
        
        Args:
            phases: List of pipeline phases
            
        Raises:
            ConfigurationError: If phase dependencies are invalid
        """
        phase_names = set()
        for phase in phases:
            for phase_name, phase_config in phase.items():
                if phase_name in phase_names:
                    raise ConfigurationError(
                        "Duplicate phase name",
                        context=ErrorContext(
                            component='pipeline_manager',
                            operation='validate_phases',
                            details={'phase': phase_name}
                        )
                    )
                phase_names.add(phase_name)
                
                # Check output directory
                if not phase_config.get('output_dir'):
                    self.error_tracker.add_warning(
                        'pipeline_manager',
                        f"Missing output directory for phase {phase_name}",
                        {
                            'phase': phase_name,
                            'is_critical': False
                        }
                    )
    
    def _validate_component_dependencies(
        self,
        components: Dict[str, Dict[str, Any]]
    ) -> None:
        """Validate component dependencies and configurations.
        
        Args:
            components: Component configurations
            
        Raises:
            ConfigurationError: If component dependencies are invalid
        """
        required_components = {
            'MARKDOWN_PARSE': {'markdown_processor'},
            'MARKDOWN_CONSOLIDATE': {'markdown_processor'},
            'MARKDOWN_AGGREGATE': {'markdown_processor'},
            'MARKDOWN_SPLIT_THREEFILES': {'markdown_processor'}
        }
        
        # Check for required components
        for phase_name, required in required_components.items():
            missing = required - set(components.keys())
            if missing:
                self.error_tracker.add_warning(
                    'pipeline_manager',
                    f"Missing required components for phase {phase_name}: {missing}",
                    {
                        'phase': phase_name,
                        'missing_components': list(missing)
                    }
                )
    
    @with_retry(max_attempts=3, delay=1.0)
    @handle_errors(reraise=True)
    async def load_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load and validate pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
            
        Returns:
            Validation report dictionary
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate configuration
            is_valid = self.schema_validator.validate_config(config)
            if not is_valid:
                # Get validation report
                validation_report = self.schema_validator.get_validation_report()
                
                # Add validation errors to error tracker
                for error in validation_report['errors']:
                    self.error_tracker.add_error(
                        component='pipeline_manager',
                        message=error['message'],
                        context={'path': '', 'is_critical': True}
                    )
                
                # Add validation warnings to error tracker
                for warning in validation_report['warnings']:
                    self.error_tracker.add_warning(
                        component='pipeline_manager',
                        message=warning['message'],
                        context={'path': '', 'is_critical': False}
                    )
                
                # Return validation report
                return self.get_validation_report()
            
            # Store configuration
            self._config = config
            
            # Process components
            pipeline_config = config.get('pipeline', {})
            components = pipeline_config.get('components', {})
            for component_name, component_config in components.items():
                try:
                    self._components[component_name] = self.component_handler.apply_config(
                        component_name, component_config
                    )
                except Exception as e:
                    self.error_tracker.add_error(
                        component='pipeline_manager',
                        message=str(e),
                        context={'component': component_name}
                    )
            
            # Return validation report
            return self.get_validation_report()
            
        except Exception as e:
            # Add error to tracker
            self.error_tracker.add_error(
                component='pipeline_manager',
                message=str(e),
                context={'path': '', 'is_critical': True}
            )
            
            # Return validation report
            return self.get_validation_report() 

    def register_processor(self, name: str, processor: Any) -> None:
        """Register a processor with the pipeline.
        
        Args:
            name: Name of the processor
            processor: Processor instance
        """
        self._components[name] = processor
        self.logger.debug(f"Registered processor: {name}")

    async def run(self) -> bool:
        """Run the pipeline.
        
        Returns:
            True if pipeline completed successfully, False otherwise
        """
        try:
            for name, processor in self._components.items():
                self.logger.info(f"Running processor: {name}")
                
                # Set up processor
                try:
                    self.logger.debug(f"Setting up processor: {name}")
                    await processor.setup()
                except Exception as e:
                    self.logger.error(f"Failed to set up processor {name}: {str(e)}")
                    return False
                
                # Run processor
                try:
                    success = await processor.process()
                    if not success:
                        self.logger.error(f"Processor failed: {name}")
                        return False
                except Exception as e:
                    self.logger.error(f"Error running processor {name}: {str(e)}")
                    return False
                finally:
                    # Clean up processor
                    try:
                        await processor.cleanup()
                    except Exception as e:
                        self.logger.error(f"Failed to clean up processor {name}: {str(e)}")
                        
            return True
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return False 