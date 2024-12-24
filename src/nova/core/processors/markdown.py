"""Markdown processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List

import markdown

from .base import BaseProcessor
from ..config.base import ProcessorConfig
from ..errors import ProcessingError
from ..utils.paths import ensure_dir

class MarkdownProcessor(BaseProcessor):
    """Processor for parsing and processing markdown files."""
    
    def __init__(self, config: ProcessorConfig):
        """Initialize the processor.
        
        Args:
            config: Processor configuration
        """
        super().__init__(config)
        self.parser = markdown.Markdown(extensions=['extra'])
        self.handlers = []
        self._initialize_handlers()
    
    def _initialize_handlers(self) -> None:
        """Initialize markdown handlers."""
        # Get handler configs
        handler_configs = self.get_option('handlers', [])
        
        # Initialize each handler
        for handler_config in handler_configs:
            handler_type = handler_config.get('type')
            if not handler_type:
                self.log_warning(f"Missing handler type in config: {handler_config}")
                continue
                
            try:
                # Import handler class
                module_path, class_name = handler_type.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                handler_class = getattr(module, class_name)
                
                # Create handler instance
                handler = handler_class(handler_config)
                self.handlers.append(handler)
                
            except (ImportError, AttributeError) as e:
                self.log_error(f"Failed to load handler {handler_type}: {str(e)}")
    
    def validate_config(self) -> None:
        """Validate processor configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        super().validate_config()
        
        # Check required paths
        if not self.config.input_dir:
            raise ValueError("input_dir must be specified in config")
            
        if not self.config.output_dir:
            raise ValueError("output_dir must be specified in config")
            
        # Validate parser config
        parser_config = self.get_option('parser', {})
        if not isinstance(parser_config, dict):
            raise ValueError("parser config must be a dictionary")
    
    async def process_file(
        self,
        input_path: Path,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a single markdown file.
        
        Args:
            input_path: Path to input file
            context: Optional processing context
            
        Returns:
            Dict containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Read input file
            content = input_path.read_text(encoding='utf-8')
            
            # Parse markdown
            html = self.parser.convert(content)
            
            # Process through handlers
            result = {
                'content': html,
                'metadata': {
                    'input_path': str(input_path),
                    'handlers': {}
                }
            }
            
            for handler in self.handlers:
                handler_result = await handler.process(html, context)
                
                # Update content and metadata
                result['content'] = handler_result.get('content', result['content'])
                result['metadata']['handlers'][handler.__class__.__name__] = handler_result.get('metadata', {})
            
            return result
            
        except Exception as e:
            raise ProcessingError(f"Failed to process {input_path}: {str(e)}") from e
    
    async def process(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process all markdown files in input directory.
        
        Args:
            content: Not used for this processor
            context: Optional processing context
            
        Returns:
            Dict containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Validate config
            self.validate_config()
            
            # Get input/output dirs
            input_dir = self.config.input_dir
            output_dir = self.config.output_dir
            
            # Ensure output dir exists
            ensure_dir(output_dir)
            
            # Process all markdown files
            results = []
            for input_path in input_dir.rglob('*.md'):
                # Get relative path
                rel_path = input_path.relative_to(input_dir)
                output_path = output_dir / rel_path
                
                # Process file
                self.log_info(f"Processing {rel_path}")
                result = await self.process_file(input_path, context)
                
                # Write output
                ensure_dir(output_path.parent)
                output_path.write_text(result['content'], encoding='utf-8')
                
                # Store result
                results.append(result)
            
            return {
                'content': '',  # No aggregated content
                'metadata': {
                    'files_processed': len(results),
                    'results': results
                }
            }
            
        except Exception as e:
            raise ProcessingError(f"Markdown processing failed: {str(e)}") from e 