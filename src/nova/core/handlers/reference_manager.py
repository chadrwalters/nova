"""Reference management components for Nova processors."""

# Standard library imports
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

# Nova package imports
from nova.core.errors import ProcessingError
from nova.core.handlers.base import BaseHandler

class ReferenceManager(BaseHandler):
    """Manages references and links in markdown content."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize reference manager.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.config = config or {}
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be handled.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file is markdown
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}
    
    async def process(self, input_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process references in markdown file.
        
        Args:
            input_path: Path to input file
            context: Processing context
            
        Returns:
            Dict containing:
                - updated_references: List of updated references
                - errors: List of processing errors
        """
        result = {
            'updated_references': [],
            'errors': []
        }
        
        try:
            # Get processed images from context
            processed_images = context.get('processed_images', [])
            if not processed_images:
                return result
            
            # Read markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update image references
            for image_path in processed_images:
                image_name = Path(image_path).name
                # Find and update references to this image
                pattern = rf'!\[([^\]]*)\]\([^)]*{re.escape(image_name)}\)'
                matches = re.finditer(pattern, content)
                for match in matches:
                    old_ref = match.group(0)
                    new_ref = f'![{match.group(1)}]({image_name})'
                    content = content.replace(old_ref, new_ref)
                    result['updated_references'].append({
                        'old': old_ref,
                        'new': new_ref
                    })
            
            # Write updated content
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
        except Exception as e:
            error = f"Failed to update references in {input_path}: {str(e)}"
            result['errors'].append(error)
        
        return result