"""Processor for consolidating markdown files."""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from nova.core.logging import get_logger
from nova.core.pipeline.base import BaseProcessor
from nova.models.processor_result import ProcessorResult
from nova.core.file_info_provider import FileInfoProvider

logger = get_logger(__name__)

class MarkdownConsolidateProcessor(BaseProcessor):
    """Processor for consolidating markdown files."""
    
    def _add_section_markers(self, content: str) -> str:
        """Add section markers to content if they don't exist."""
        lines = content.splitlines()
        output_lines = []
        current_section = None
        
        for line in lines:
            # Check for section headers
            if line.strip().startswith('# ') or line.strip().startswith('## '):
                lower_line = line.lower()
                if 'summary' in lower_line or 'overview' in lower_line:
                    if current_section != 'summary':
                        output_lines.append('--==SUMMARY==--')
                        current_section = 'summary'
                elif 'raw notes' in lower_line or 'notes' in lower_line or 'journal' in lower_line:
                    if current_section != 'raw_notes':
                        output_lines.append('--==RAW_NOTES==--')
                        current_section = 'raw_notes'
                elif 'attachments' in lower_line:
                    if current_section != 'attachments':
                        output_lines.append('--==ATTACHMENTS==--')
                        current_section = 'attachments'
            
            output_lines.append(line)
        
        return '\n'.join(output_lines)
    
    async def process(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Process markdown files in the input directory.
        
        Args:
            input_dir: Directory containing markdown files
            output_dir: Directory to write consolidated files to
            context: Processing context
            
        Returns:
            ProcessorResult containing success/failure and any errors
        """
        result = ProcessorResult()
        context = context or {}
        
        try:
            # Use provided directories or get from environment
            input_dir = input_dir or Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'))
            output_dir = output_dir or Path(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))
            
            logger.debug(f"Using input directory: {input_dir}")
            logger.debug(f"Using output directory: {output_dir}")
            
            # Ensure directories exist
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get file info provider from context or create new one
            file_info_provider = context.get('file_info_provider') or FileInfoProvider()
            
            # Find all markdown files
            markdown_files = list(input_dir.rglob('*.md'))
            if not markdown_files:
                logger.warning(f"No markdown files found in {input_dir}")
                result.success = True
                return result
            
            logger.debug(f"Found {len(markdown_files)} markdown files")
            
            # Process each file
            for file_path in markdown_files:
                try:
                    # Get file info
                    file_info = await file_info_provider.get_file_info(file_path)
                    
                    # Skip non-markdown files
                    if not (file_info.content_type == 'text/markdown' or file_path.suffix.lower() == '.md'):
                        continue
                    
                    # Read content
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Add section markers if needed
                    content = self._add_section_markers(content)
                    
                    # Create output path preserving directory structure
                    if str(file_path).startswith(str(os.environ.get('NOVA_INPUT_DIR'))):
                        rel_path = file_path.relative_to(Path(os.environ.get('NOVA_INPUT_DIR')))
                    else:
                        rel_path = file_path.relative_to(input_dir)
                    
                    output_path = output_dir / rel_path
                    
                    # Create output directory
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Process attachments if they exist
                    attachments_dir = file_path.parent / file_path.stem
                    if attachments_dir.exists() and attachments_dir.is_dir():
                        output_attachments_dir = output_path.parent / output_path.stem
                        output_attachments_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy all files from attachment directory
                        for attachment in attachments_dir.iterdir():
                            if attachment.is_file():
                                # Copy attachment preserving metadata
                                shutil.copy2(attachment, output_attachments_dir / attachment.name)
                                
                                # Add attachment block to content if not already present
                                attachment_block = (
                                    f"\n--==ATTACHMENT_BLOCK: {attachment.name}==--\n"
                                    f"![{attachment.stem}]({output_path.stem}/{attachment.name})\n"
                                    f"--==ATTACHMENT_BLOCK_END==--\n"
                                )
                                if attachment_block not in content:
                                    content += attachment_block
                    
                    # Write consolidated content
                    output_path.write_text(content, encoding='utf-8')
                    result.processed_files.append(output_path)
                    logger.debug(f"Processed {file_path} -> {output_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to process {file_path}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
            
            result.success = True
            logger.info(f"Successfully processed {len(result.processed_files)} files")
            
        except Exception as e:
            error_msg = f"Consolidation phase failed: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            result.success = False
        
        return result