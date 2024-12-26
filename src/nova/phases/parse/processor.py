"""Processor for the parse phase."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import re
import yaml
import json

from ...core.errors import ProcessorError
from ...core.logging import get_logger
from ...core.config.base import HandlerConfig
from ..core.base_processor import BaseProcessor, ProcessorResult
from ...core.config import PipelineConfig, ProcessorConfig
from .handlers.markdown import MarkdownHandler, ConsolidationHandler
from .handlers.office.office_handler import OfficeHandler
from .handlers.image.image_handler import ImageHandler
from .handlers.text.text_handler import TextHandler

logger = get_logger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files in the parse phase."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize the processor."""
        super().__init__(processor_config, pipeline_config)
        
        # Set up logging
        self.logger = get_logger(self.__class__.__name__)
        
        # Get directories from environment
        self.input_dir = Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))
        self.output_dir = Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))
        
        # Initialize handlers
        self.handlers = []
        
        # Add default handlers
        markdown_config = {
            'type': 'markdown',
            'base_handler': 'nova.phases.core.base_handler.BaseHandler',
            'document_conversion': True,
            'image_processing': True,
            'metadata_preservation': True,
            'base_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
            'input_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
            'output_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
            'analyze_images': processor_config.components.get('markdown_processor', {}).get('analyze_images', False)
        }
        self.handlers.append(MarkdownHandler(markdown_config))
        
        office_config = {
            'type': 'office',
            'base_handler': 'nova.phases.core.base_handler.BaseHandler',
            'base_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
            'input_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
            'output_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
            'analyze_images': processor_config.components.get('office_processor', {}).get('analyze_images', False)
        }
        self.handlers.append(OfficeHandler(office_config))
        
        image_config = {
            'type': 'image',
            'base_handler': 'nova.phases.core.base_handler.BaseHandler',
            'base_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
            'input_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
            'output_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
            'analyze_images': processor_config.components.get('image_processor', {}).get('analyze_images', False)
        }
        self.handlers.append(ImageHandler(image_config))
        
        text_config = {
            'type': 'text',
            'base_handler': 'nova.phases.core.base_handler.BaseHandler',
            'base_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
            'input_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
            'output_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
            'analyze_images': processor_config.components.get('text_processor', {}).get('analyze_images', False)
        }
        self.handlers.append(TextHandler(text_config))
    
    async def process(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Process files.
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            context: Processing context
            
        Returns:
            ProcessorResult containing success/failure and any errors
        """
        try:
            # Start phase tracking
            total_files = context.get('total_files', 0) if context else 0
            self._start_phase(total_files)
            
            # Get input files
            input_dir = input_dir or self.input_dir
            output_dir = output_dir or self.output_dir
            
            # Find markdown files recursively
            markdown_files = list(input_dir.rglob('*.md'))
            logger.info(f"Found {len(markdown_files)} markdown files in {input_dir}")
            
            # Process each file
            processed_files = []
            errors = []
            
            for i, file in enumerate(markdown_files):
                try:
                    # Update progress
                    self._update_phase_progress(
                        processed_files=i,
                        current_file=str(file)
                    )
                    
                    # Process file
                    result = await self._process_file(file)
                    
                    if result.success:
                        processed_files.append(file)
                    else:
                        errors.extend(result.errors)
                        
                except Exception as e:
                    logger.error(f"Failed to process file {file}: {e}")
                    errors.append(str(e))
            
            # Complete phase tracking
            self._complete_phase()
            
            return ProcessorResult(
                success=len(errors) == 0,
                processed_files=processed_files,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Failed to process files: {e}")
            return ProcessorResult(
                success=False,
                errors=[str(e)]
            )
    
    async def _process_file(self, input_file: Path) -> ProcessorResult:
        """Process a single file.
        
        Args:
            input_file: Path to the file to process
            
        Returns:
            ProcessorResult containing success/failure and any errors
        """
        try:
            # Read content
            content = input_file.read_text(encoding='utf-8')
            
            # Extract frontmatter
            frontmatter = {}
            content_lines = content.split('\n')
            if content_lines and content_lines[0].strip() == '---':
                end_idx = next((i for i, line in enumerate(content_lines[1:], 1) if line.strip() == '---'), -1)
                if end_idx > 0:
                    try:
                        frontmatter = yaml.safe_load('\n'.join(content_lines[1:end_idx]))
                        content_lines = content_lines[end_idx + 1:]
                    except Exception as e:
                        self.logger.warning(f"Failed to parse frontmatter: {e}")
            
            content = '\n'.join(content_lines)
            
            # Extract code blocks
            code_blocks = []
            code_block_pattern = r'```[^\n]*\n[\s\S]*?```'
            for match in re.finditer(code_block_pattern, content):
                code_blocks.append({
                    'content': match.group(0),
                    'start': match.start(),
                    'end': match.end()
                })
            
            # Extract images
            images = []
            image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            for match in re.finditer(image_pattern, content):
                images.append({
                    'alt': match.group(1),
                    'src': match.group(2),
                    'start': match.start(),
                    'end': match.end()
                })
            
            # Build metadata structure
            metadata = {
                'frontmatter': frontmatter,
                'content_markers': {
                    'images': images,
                    'code_blocks': code_blocks
                }
            }
            
            # Process content through handlers
            processed_content = content
            for handler in self.handlers:
                try:
                    # Get attachments directory
                    attachments_dir = input_file.parent / input_file.stem
                    attachments = []
                    if attachments_dir.exists() and attachments_dir.is_dir():
                        attachments = list(attachments_dir.glob('*'))
                        logger.info(f"Found {len(attachments)} attachments in {attachments_dir}")
                    
                    # Process with handler based on its signature
                    try:
                        # Try with all arguments
                        result = await handler.process(input_file, {}, attachments)
                    except TypeError:
                        try:
                            # Try with just file and context
                            result = await handler.process(input_file, {})
                        except TypeError:
                            # Try with just file
                            result = await handler.process(input_file)
                    
                    # Convert dictionary result to ProcessorResult if needed
                    if isinstance(result, dict):
                        result = ProcessorResult(
                            success=True,
                            content=result.get('content', ''),
                            metadata=result.get('metadata', {}),
                            errors=result.get('errors', [])
                        )
                    
                    if result and result.content:
                        processed_content = result.content
                except Exception as e:
                    self.logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
            
            return ProcessorResult(
                success=True,
                content=processed_content,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process file {input_file}: {e}")
            return ProcessorResult(
                success=False,
                errors=[str(e)]
            ) 