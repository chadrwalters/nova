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
            
            # Read the original markdown content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find attachments in two ways:
            # 1. Directory with same name as markdown file
            # 2. Other markdown files in the same directory
            attachments = []
            
            # Case 1: Directory with same name as markdown file
            attachments_dir = input_path.parent / input_path.stem
            if attachments_dir.is_dir():
                # Process all markdown files in attachments directory
                for attachment_path in sorted(attachments_dir.rglob('*.md')):
                    try:
                        with open(attachment_path, 'r', encoding='utf-8') as f:
                            attachment_content = f.read()
                        
                        # Add attachment markers and content
                        rel_path = attachment_path.relative_to(attachments_dir)
                        content += f"\n\n[Begin Attachment: {rel_path}]\n\n{attachment_content}\n\n[End Attachment: {rel_path}]\n"
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process attachment {attachment_path}: {e}")
            
            # Case 2: Other markdown files in the same directory
            if input_path.parent.name != input_path.stem:  # Only if not in its own directory
                for sibling in sorted(input_path.parent.glob('*.md')):
                    if sibling != input_path:  # Skip the main file
                        try:
                            with open(sibling, 'r', encoding='utf-8') as f:
                                attachment_content = f.read()
                            
                            # Add attachment markers and content
                            rel_path = sibling.relative_to(input_path.parent)
                            content += f"\n\n[Begin Attachment: {rel_path}]\n\n{attachment_content}\n\n[End Attachment: {rel_path}]\n"
                            
                        except Exception as e:
                            self.logger.error(f"Failed to process attachment {sibling}: {e}")
            
            # Write consolidated content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to consolidate markdown file {input_path}: {str(e)}") from e