"""Three-file split processor for markdown content.

This module provides functionality for splitting markdown content into three separate files:
1. summary.md - Contains high-level overview and key points
2. raw_notes.md - Contains detailed notes and chronological entries
3. attachments.md - Contains embedded content and file attachments
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import logging
import re
import json
from datetime import datetime

from ..core.base import BaseProcessor
from ..core.config import NovaConfig, ProcessorConfig, ThreeFileSplitConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor that splits content into summary, raw notes, and attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig) -> None:
        """Initialize the processor.
        
        Args:
            processor_config: Configuration specific to this processor
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.output_files = processor_config.output_files
        self.section_markers = processor_config.section_markers
        self.attachment_markers = processor_config.attachment_markers
        self.content_type_rules = processor_config.content_type_rules
        self.content_preservation = processor_config.content_preservation
        self.cross_linking = processor_config.cross_linking
        self.preserve_headers = processor_config.preserve_headers

        # Initialize state
        self.stats = {
            'total_content_size': 0,
            'summary_size': 0,
            'raw_notes_size': 0,
            'attachments_size': 0,
            'headers_processed': 0,
            'attachments_processed': 0
        }

    def _setup(self) -> None:
        """Setup processor requirements."""
        super()._setup()
        
        # Create output directories
        output_dir = self.nova_config.paths.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create processing directory
        processing_dir = self.nova_config.paths.processing_dir
        processing_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory
        temp_dir = self.nova_config.paths.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)

    def process(self, content: str, **kwargs: Any) -> str:
        """Process the content by splitting it into three files.
        
        Args:
            content: The content to process
            **kwargs: Additional arguments for processing
        
        Returns:
            The processed content
        """
        # Extract attachment blocks
        cleaned_content, attachments = self._extract_attachment_blocks(content)

        # Split content into sections
        sections = self._split_content(cleaned_content)

        # Write sections to files
        self._write_sections(sections)

        # Write attachments
        self._write_attachments(attachments)

        return content

    def _extract_attachment_blocks(self, content: str) -> Tuple[str, List[Dict[str, str]]]:
        """Extract attachment blocks from content.
        
        Args:
            content: The content to process
        
        Returns:
            Tuple of (cleaned content, list of attachment blocks)
        """
        attachments = []
        lines = content.split('\n')
        cleaned_lines = []
        in_block = False
        current_block = None

        for line in lines:
            if not in_block:
                if line.startswith(self.attachment_markers['start'].format(filename='')):
                    in_block = True
                    filename = line[len(self.attachment_markers['start'].format(filename='')):-2]
                    current_block = {'filename': filename, 'content': []}
                else:
                    cleaned_lines.append(line)
            else:
                if line == self.attachment_markers['end']:
                    in_block = False
                    if current_block:
                        current_block['content'] = '\n'.join(current_block['content'])
                        attachments.append(current_block)
                        current_block = None
                else:
                    current_block['content'].append(line)

        return '\n'.join(cleaned_lines), attachments

    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into sections.
        
        Args:
            content: The content to split
        
        Returns:
            Dictionary of section name to content
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        current_section = None
        lines = content.split('\n')

        for line in lines:
            if line in self.section_markers.values():
                current_section = next(k for k, v in self.section_markers.items() if v == line)
            elif current_section:
                sections[current_section].append(line)

        return {k: '\n'.join(v) for k, v in sections.items()}

    def _write_sections(self, sections: Dict[str, str]) -> None:
        """Write sections to files.
        
        Args:
            sections: Dictionary of section name to content
        """
        output_dir = self.nova_config.paths.output_dir
        for section_name, content in sections.items():
            output_path = output_dir / self.output_files[section_name]
            output_path.write_text(content)

    def _write_attachments(self, attachments: List[Dict[str, str]]) -> None:
        """Write attachments to files.
        
        Args:
            attachments: List of attachment blocks
        """
        output_dir = self.nova_config.paths.output_dir
        attachments_file = output_dir / self.output_files['attachments']
        
        with attachments_file.open('a') as f:
            for attachment in attachments:
                f.write(f"{self.attachment_markers['start'].format(filename=attachment['filename'])}\n")
                f.write(attachment['content'])
                f.write(f"\n{self.attachment_markers['end']}\n\n")