"""Consolidation handlers for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from .base import BaseHandler
from ..errors import HandlerError
from ..utils.paths import ensure_dir, copy_file

class ConsolidationHandler(BaseHandler):
    """Handler for consolidating markdown files with attachments."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.copy_attachments = config.get('copy_attachments', True)
        self.update_references = config.get('update_references', True)
        self.attachment_dir = config.get('attachment_dir', 'attachments')
    
    def validate_config(self) -> None:
        """Validate handler configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        super().validate_config()
        
        # Check boolean options
        for option in ['copy_attachments', 'update_references']:
            value = self.config.get(option)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{option} must be a boolean")
        
        # Check attachment directory
        attachment_dir = self.config.get('attachment_dir')
        if attachment_dir and not isinstance(attachment_dir, str):
            raise ValueError("attachment_dir must be a string")
    
    def _find_attachments(self, content: str, base_path: Path) -> List[Path]:
        """Find attachments referenced in content.
        
        Args:
            content: Content to search
            base_path: Base path for resolving relative paths
            
        Returns:
            List of attachment paths
        """
        attachments = []
        
        # TODO: Implement attachment finding logic
        # This should look for image references, links, etc.
        # and resolve them to absolute paths
        
        return attachments
    
    def _copy_attachment(self, source: Path, dest_dir: Path) -> Path:
        """Copy attachment to destination directory.
        
        Args:
            source: Source file path
            dest_dir: Destination directory
            
        Returns:
            Path to copied file
            
        Raises:
            HandlerError: If copy fails
        """
        try:
            # Create destination directory
            ensure_dir(dest_dir)
            
            # Copy file
            dest_path = dest_dir / source.name
            copy_file(source, dest_path)
            
            return dest_path
            
        except Exception as e:
            raise HandlerError(f"Failed to copy attachment {source}: {str(e)}") from e
    
    def _update_reference(self, content: str, old_path: Path, new_path: Path) -> str:
        """Update attachment reference in content.
        
        Args:
            content: Content to update
            old_path: Old attachment path
            new_path: New attachment path
            
        Returns:
            Updated content
        """
        # TODO: Implement reference updating logic
        # This should update image references, links, etc.
        # to point to the new attachment locations
        
        return content
    
    async def process(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process content and consolidate attachments.
        
        Args:
            content: Content to process
            context: Optional processing context
            
        Returns:
            Dict containing processing results
            
        Raises:
            HandlerError: If processing fails
        """
        try:
            # Validate config
            self.validate_config()
            
            # Get base path from context
            base_path = context.get('base_path')
            if not base_path:
                raise HandlerError("base_path must be provided in context")
            base_path = Path(base_path)
            
            # Initialize result
            result = {
                'content': content,
                'metadata': {
                    'attachments': [],
                    'changes': []
                }
            }
            
            # Find attachments
            attachments = self._find_attachments(content, base_path)
            
            # Process attachments if enabled
            if self.copy_attachments:
                # Create attachment directory
                attachment_dir = base_path / self.attachment_dir
                ensure_dir(attachment_dir)
                
                # Copy each attachment
                for attachment in attachments:
                    # Copy file
                    new_path = self._copy_attachment(attachment, attachment_dir)
                    
                    # Update reference if enabled
                    if self.update_references:
                        result['content'] = self._update_reference(
                            result['content'],
                            attachment,
                            new_path
                        )
                    
                    # Track changes
                    result['metadata']['attachments'].append({
                        'original_path': str(attachment),
                        'new_path': str(new_path)
                    })
                    result['metadata']['changes'].append(
                        f"Copied attachment: {attachment.name}"
                    )
            
            return result
            
        except Exception as e:
            raise HandlerError(f"Consolidation failed: {str(e)}") from e 