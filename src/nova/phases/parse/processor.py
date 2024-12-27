"""Markdown parse processor."""

from pathlib import Path
from typing import Dict, Any, Optional

import markitdown

from nova.core.pipeline.processor import PipelineProcessor
from nova.core.errors import ValidationError, ProcessingError


class MarkdownParseProcessor(PipelineProcessor):
    """Processor for parsing markdown files."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize processor.
        
        Args:
            config: Processor configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        super().__init__(config)
        
        # Initialize markdown parser
        parser_config = self.config.get("markdown_processor", {})
        self.parser = markitdown.Parser(**parser_config)
        
        # Initialize handlers
        self.handlers = []
        self._initialize_handlers()
        
    def _initialize_handlers(self) -> None:
        """Initialize markdown handlers."""
        handlers_config = self.config.get("handlers", {})
        if not isinstance(handlers_config, dict):
            raise ValidationError("Invalid handlers configuration")
            
        for name, config in handlers_config.items():
            if not isinstance(config, dict):
                raise ValidationError(f"Invalid handler configuration: {name}")
                
            # Import handler class
            try:
                handler_class = self._import_handler(config["base_handler"])
                handler = handler_class(config)
                self.handlers.append(handler)
            except Exception as e:
                raise ValidationError(f"Failed to initialize handler {name}: {str(e)}")
                
    def _import_handler(self, handler_path: str) -> type:
        """Import handler class.
        
        Args:
            handler_path: Full path to handler class
            
        Returns:
            Handler class
            
        Raises:
            ValidationError: If handler cannot be imported
        """
        try:
            module_path, class_name = handler_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        except Exception as e:
            raise ValidationError(f"Failed to import handler: {str(e)}")
            
    def process(self, input_file: Path) -> None:
        """Process markdown file.
        
        Args:
            input_file: Input file path
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Validate input file
            if not input_file.suffix.lower() in [".md", ".markdown"]:
                raise ValidationError("Not a markdown file")
                
            # Parse markdown
            with open(input_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            document = self.parser.parse(content)
            
            # Process with handlers
            for handler in self.handlers:
                if handler.can_handle(document):
                    handler.process(document)
                    
            # Write output
            output_file = self.output_dir / input_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(str(document))
                
            # Track metrics
            self.metrics.increment_counter("files_processed")
            self.monitoring.record_metric(
                name="file_processed",
                value=str(input_file),
                tags={"phase": "markdown_parse"}
            )
                
        except Exception as e:
            raise ProcessingError(f"Failed to process {input_file}: {str(e)}")
            
    def cleanup(self) -> None:
        """Clean up processor resources."""
        super().cleanup()
        
        # Clean up handlers
        for handler in self.handlers:
            handler.cleanup() 