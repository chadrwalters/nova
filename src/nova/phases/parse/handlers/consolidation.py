"""Handler for consolidating markdown files."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import shutil

from ....core.base_handler import BaseHandler
from ....core.models.result import ProcessingResult


class ConsolidationHandler(BaseHandler):
    """Handler for consolidating markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
    async def can_handle(self, file_path: Union[str, Path]) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        # Convert string path to Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Union[str, Path], context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing parsed content and metadata
        """
        try:
            # Convert string path to Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            # Read input file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get output directory
            output_dir = Path(context['output_dir']) if context and 'output_dir' in context else None
            if not output_dir:
                raise ValueError("No output directory specified")
            
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to output directory
            output_file = output_dir / file_path.name
            shutil.copy2(file_path, output_file)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=content,
                metadata={'output_file': str(output_file)}
            )
            result.add_processed_file(file_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            return ProcessingResult(success=False, errors=[error_msg])
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def cleanup(self) -> None:
        """Clean up resources.
        
        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        pass 