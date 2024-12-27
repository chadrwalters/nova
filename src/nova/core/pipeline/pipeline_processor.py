"""Pipeline processor."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from nova.core.pipeline.errors import ValidationError
from nova.core.pipeline.types import ProcessingResult
from nova.core.pipeline.base_handler import BaseHandler


class PipelineProcessor:
    """Base class for pipeline processors."""

    def __init__(self, processor_config: Dict[str, Any], pipeline_config: Optional[Dict[str, Any]] = None):
        """Initialize pipeline processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.name = processor_config.get('name', self.__class__.__name__)
        self.description = processor_config.get('description', '')
        self.options = processor_config.get('options', {})
        self.components = processor_config.get('components', {})
        self.output_dir = processor_config.get('output_dir')
        self.dependencies = processor_config.get('dependencies', [])
        self.pipeline_config = pipeline_config or {}
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, BaseHandler] = {}

    def validate(self) -> None:
        """Validate processor configuration.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.name:
            raise ValidationError("Processor name is required")

        if not self.output_dir:
            raise ValidationError("Output directory is required")

        if not isinstance(self.components, dict):
            raise ValidationError("Components must be a dictionary")

        for component_name, component_config in self.components.items():
            if not isinstance(component_config, dict):
                raise ValidationError(f"Component {component_name} configuration must be a dictionary")

            if 'handler' not in component_config:
                raise ValidationError(f"Component {component_name} must specify a handler")

    def get_handler(self, handler_type: Type[BaseHandler], config: Dict[str, Any]) -> BaseHandler:
        """Get or create handler instance.
        
        Args:
            handler_type: Handler class
            config: Handler configuration
            
        Returns:
            Handler instance
        """
        handler_key = f"{handler_type.__name__}_{id(config)}"
        if handler_key not in self._handlers:
            self._handlers[handler_key] = handler_type(config)
        return self._handlers[handler_key]

    async def process(self, input_files: List[Path]) -> ProcessingResult:
        """Process input files.
        
        Args:
            input_files: List of input files
            
        Returns:
            Processing result
        """
        try:
            # Validate configuration
            self.validate()

            # Initialize result
            result = ProcessingResult(
                success=True,
                processed_files=[],
                metadata={},
                content=None
            )

            # Process each file
            for file_path in input_files:
                file_result = await self._process_file(file_path)
                if not file_result.success:
                    result.success = False
                    result.errors.extend(file_result.errors)
                    continue

                result.processed_files.extend(file_result.processed_files)
                result.metadata.update(file_result.metadata)

            return result

        except Exception as e:
            error_msg = f"Error in processor {self.name}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    async def _process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Processing result
        """
        try:
            # Find suitable handler
            handler = None
            for component_name, component_config in self.components.items():
                handler_type = component_config.get('handler')
                if not handler_type:
                    continue

                handler = self.get_handler(handler_type, component_config)
                if handler.can_handle(file_path):
                    break

            if not handler:
                return ProcessingResult(
                    success=False,
                    errors=[f"No suitable handler found for {file_path}"]
                )

            # Process file
            return await handler.process(file_path)

        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    async def cleanup(self) -> None:
        """Clean up processor resources."""
        for handler in self._handlers.values():
            await handler.cleanup() 