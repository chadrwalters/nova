"""Handler for consolidating markdown files."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..errors import PipelineError
from ..utils.paths import ensure_directory, copy_file

class ConsolidateHandler:
    """Handler for consolidating markdown files with their attachments."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize consolidate handler.
        
        Args:
            config: Handler configuration
        """
        self.config = config
        self.base_handler = config.get('base_handler')
        self.copy_attachments = config.get('copy_attachments', True)
        self.update_references = config.get('update_references', True)
        
    def consolidate_files(self, files: List[Path], output_dir: Path) -> None:
        """Consolidate markdown files with their attachments.
        
        Args:
            files: List of markdown files to consolidate
            output_dir: Output directory
        """
        try:
            for file in files:
                self._consolidate_file(file, output_dir)
                
        except Exception as e:
            raise PipelineError(f"Failed to consolidate files: {e}")
            
    def _consolidate_file(self, file: Path, output_dir: Path) -> None:
        """Consolidate single markdown file.
        
        Args:
            file: Markdown file to consolidate
            output_dir: Output directory
        """
        try:
            # Create output directory
            dest_dir = output_dir / file.parent.name
            ensure_directory(dest_dir)
            
            # Copy markdown file
            dest_file = dest_dir / file.name
            copy_file(file, dest_file)
            
            # Copy attachments if enabled
            if self.copy_attachments:
                self._copy_attachments(file, dest_dir)
                
            # Update references if enabled
            if self.update_references:
                self._update_references(dest_file)
                
        except Exception as e:
            raise PipelineError(f"Failed to consolidate file {file}: {e}")
            
    def _copy_attachments(self, file: Path, dest_dir: Path) -> None:
        """Copy file attachments.
        
        Args:
            file: Source markdown file
            dest_dir: Destination directory
        """
        try:
            # Get attachment directory
            attachment_dir = file.parent / 'attachments'
            if not attachment_dir.exists():
                return
                
            # Create destination attachment directory
            dest_attachment_dir = dest_dir / 'attachments'
            ensure_directory(dest_attachment_dir)
            
            # Copy attachments
            for attachment in attachment_dir.iterdir():
                if attachment.is_file():
                    dest_attachment = dest_attachment_dir / attachment.name
                    copy_file(attachment, dest_attachment)
                    
        except Exception as e:
            raise PipelineError(f"Failed to copy attachments for {file}: {e}")
            
    def _update_references(self, file: Path) -> None:
        """Update file references.
        
        Args:
            file: Markdown file to update
        """
        try:
            # Read file content
            content = file.read_text()
            
            # Update attachment references
            content = self._update_attachment_refs(content)
            
            # Write updated content
            file.write_text(content)
            
        except Exception as e:
            raise PipelineError(f"Failed to update references in {file}: {e}")
            
    def _update_attachment_refs(self, content: str) -> str:
        """Update attachment references in content.
        
        Args:
            content: File content
            
        Returns:
            Updated content
        """
        try:
            # TODO: Implement reference updating
            return content
            
        except Exception as e:
            raise PipelineError(f"Failed to update attachment references: {e}")
            
    def __str__(self) -> str:
        """Get string representation.
        
        Returns:
            String representation
        """
        return f"ConsolidateHandler(copy_attachments={self.copy_attachments}, update_references={self.update_references})" 