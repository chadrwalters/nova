"""Markdown consolidation processor for merging markdown files with their attachments."""

import os
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re

from .base import BaseProcessor
from ..core.config import NovaConfig, ProcessorConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger
from ..core.summary import ProcessingSummary

class MarkdownConsolidateProcessor(BaseProcessor):
    """Processor for consolidating markdown files with their attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
    def _setup(self) -> None:
        """Setup processor requirements."""
        # No special setup needed for consolidation
        pass
        
    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process markdown files by consolidating with attachments.
        
        Args:
            input_path: Path to input markdown file
            output_path: Path to output consolidated file
            
        Returns:
            Path to processed file
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Find any attachments directory matching the markdown file
            attachments_dir = self._find_attachments_dir(input_path)
            
            # Read the original markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # If attachments exist, process and merge them
            if attachments_dir:
                content = self._merge_attachments(content, attachments_dir)
                
            # Write consolidated content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to consolidate markdown file {input_path}: {str(e)}") from e
            
    def _find_attachments_dir(self, markdown_path: Path) -> Optional[Path]:
        """Find attachments directory for a markdown file.
        
        Args:
            markdown_path: Path to markdown file
            
        Returns:
            Path to attachments directory if it exists, None otherwise
        """
        # Check for directory with same name as markdown file
        potential_dir = markdown_path.parent / markdown_path.stem
        if potential_dir.is_dir():
            return potential_dir
        return None
        
    def _merge_attachments(self, content: str, attachments_dir: Path) -> str:
        """Merge attachments into markdown content.
        
        Args:
            content: Original markdown content
            attachments_dir: Path to attachments directory
            
        Returns:
            Consolidated markdown content
        """
        # Process each markdown file in attachments directory
        for attachment_path in attachments_dir.rglob('*.md'):
            with open(attachment_path, 'r', encoding='utf-8') as f:
                attachment_content = f.read()
                
            # Add attachment markers and content
            rel_path = attachment_path.relative_to(attachments_dir)
            content += f"\n\n[Begin Attachment: {rel_path}]\n\n{attachment_content}\n\n[End Attachment: {rel_path}]\n"
            
        return content 