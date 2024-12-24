"""Aggregate processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from .base import BaseProcessor
from ..config.base import ProcessorConfig
from ..errors import ProcessingError
from ..utils.paths import ensure_dir

class AggregateProcessor(BaseProcessor):
    """Processor for aggregating markdown files into a single file."""
    
    def __init__(self, config: ProcessorConfig):
        """Initialize the processor.
        
        Args:
            config: Processor configuration
        """
        super().__init__(config)
        self.handlers = []
        self._initialize_handlers()
    
    def _initialize_handlers(self) -> None:
        """Initialize aggregation handlers."""
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
            
        # Check required options
        output_filename = self.get_option('output_filename')
        if not output_filename:
            raise ValueError("output_filename must be specified in config")
    
    def _collect_files(self, input_dir: Path) -> List[Path]:
        """Collect markdown files to aggregate.
        
        Args:
            input_dir: Input directory path
            
        Returns:
            List of file paths to aggregate
        """
        files = []
        
        # Get all markdown files
        for file_path in input_dir.rglob('*.md'):
            files.append(file_path)
        
        # Sort files if requested
        sort_by = self.get_option('sort_by')
        if sort_by == 'name':
            files.sort()
        elif sort_by == 'date':
            files.sort(key=lambda p: p.stat().st_mtime)
        
        return files
    
    def _create_file_header(self, file_path: Path, input_dir: Path) -> str:
        """Create header for a file in the aggregated output.
        
        Args:
            file_path: Path to file
            input_dir: Input directory path
            
        Returns:
            Header string
        """
        # Get relative path
        rel_path = file_path.relative_to(input_dir)
        
        # Create header
        header = f"\n\n## Start of file: {rel_path}\n\n"
        
        # Add metadata if requested
        if self.get_option('include_metadata', False):
            stat = file_path.stat()
            header += f"- Last modified: {stat.st_mtime}\n"
            header += f"- Size: {stat.st_size} bytes\n\n"
        
        return header
    
    async def process(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Aggregate markdown files into a single file.
        
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
            
            # Get input/output paths
            input_dir = self.config.input_dir
            output_dir = self.config.output_dir
            output_path = output_dir / self.get_option('output_filename')
            
            # Ensure output dir exists
            ensure_dir(output_dir)
            
            # Initialize sections
            sections = {
                'summary': [],
                'raw_notes': [],
                'attachments': []
            }
            
            # Add section headers with markers
            sections['summary'].append("--==SUMMARY==--\n\n# Summary\n\n")
            sections['raw_notes'].append("\n--==RAW NOTES==--\n\n# Raw Notes\n\n")
            sections['attachments'].append("\n--==ATTACHMENTS==--\n\n# File Attachments\n\n")
            
            # Collect files to aggregate
            files = self._collect_files(input_dir)
            
            # Process files if found
            if files:
                # Process each file
                for file_path in files:
                    # Add file header
                    if self.get_option('include_file_headers', True):
                        sections['raw_notes'].append(self._create_file_header(file_path, input_dir))
                    
                    # Read file content
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Process through handlers
                    for handler in self.handlers:
                        handler_result = await handler.process(content, context)
                        content = handler_result.get('content', content)
                    
                    # Add content to raw notes
                    sections['raw_notes'].append(content)
                    
                    # Add separator if requested
                    if self.get_option('add_separators', True):
                        sections['raw_notes'].append("\n---\n")
            
            # Join sections
            final_content = (
                "".join(sections['summary']) +
                "".join(sections['raw_notes']) +
                "".join(sections['attachments'])
            )
            
            # Write output file
            output_path.write_text(final_content, encoding='utf-8')
            
            return {
                'content': final_content,
                'metadata': {
                    'files_processed': len(files),
                    'output_path': str(output_path),
                    'total_size': len(final_content)
                }
            }
            
        except Exception as e:
            raise ProcessingError(f"Aggregation failed: {str(e)}") from e 