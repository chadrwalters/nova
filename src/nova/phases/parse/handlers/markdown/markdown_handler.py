"""Markdown handler for processing markdown files and their attachments."""

import os
import time
import json
import shutil
import magic
import logging
import aiofiles
import yaml
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple, Union
import tempfile

from rich.console import Console
from rich.table import Table

from nova.core.logging import get_logger
from nova.models.parsed_result import ProcessingResult
from .image_converter import ImageConverter
from ..base_handler import BaseHandler
from nova.core.file_info_provider import FileInfoProvider
from nova.models.parsed_result import ParsedResult
from nova.phases.parse.handlers.markdown.document_converter import DocumentConverter
from nova.phases.parse.handlers.markdown.image_converter import ImageConverter
from nova.phases.parse.handlers.markdown.consolidation_handler import ConsolidationHandler

logger = get_logger(__name__)
console = Console()

def serialize_date(obj: Any) -> Union[str, Any]:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse frontmatter from markdown content.
    
    Args:
        content: Markdown content with optional frontmatter
        
    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    if not content.startswith('---\n'):
        return {}, content
        
    try:
        # Find the end of frontmatter
        end_index = content.find('\n---\n', 4)
        if end_index == -1:
            return {}, content
            
        # Extract and parse frontmatter
        frontmatter = content[4:end_index]
        remaining_content = content[end_index + 5:]
        
        # Parse YAML frontmatter
        metadata = yaml.safe_load(frontmatter)
        if not isinstance(metadata, dict):
            metadata = {}
            
        return metadata, remaining_content
        
    except Exception as e:
        logger.error(f"Error parsing frontmatter: {str(e)}")
        return {}, content

class MarkdownHandler(BaseHandler):
    """Handles markdown file processing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize markdown handler.
        
        Args:
            config: Configuration dictionary containing:
                analyze_images: Whether to analyze images with OpenAI Vision API
        """
        super().__init__(config)
        self.base_dir = os.environ.get('NOVA_BASE_DIR')
        self.input_dir = os.environ.get('NOVA_INPUT_DIR')
        self.output_dir = os.environ.get('NOVA_PHASE_MARKDOWN_PARSE')
        
        if not all([self.base_dir, self.input_dir, self.output_dir]):
            raise ValueError("Required environment variables not set: NOVA_BASE_DIR, NOVA_INPUT_DIR, NOVA_PHASE_MARKDOWN_PARSE")
            
        self.base_dir = Path(self.base_dir)
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        
        self.image_converter = ImageConverter(analyze_images=config.get('analyze_images', False))
        self.logger = get_logger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize file info provider
        self.file_info_provider = FileInfoProvider()
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None, attachments: Optional[List[Path]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: List of attachment paths
            
        Returns:
            ProcessingResult containing the processed content
        """
        try:
            self.logger.debug(f"Processing file: {file_path}")
            self.logger.debug(f"Context: {context}")
            self.logger.debug(f"Attachments: {attachments}")
            
            # Read markdown content
            content = file_path.read_text()
            
            # Parse frontmatter
            frontmatter, content = parse_frontmatter(content)
            
            # Process attachments
            processed_content = await self.handle(file_path, context or {})
            
            # Add metadata
            metadata = {
                'file': str(file_path),
                'processor': 'MarkdownHandler',
                'version': '1.0',
                'timestamp': datetime.now().isoformat()
            }
            metadata.update(frontmatter)  # Add frontmatter to metadata
            processed_content = f"<!-- {json.dumps(metadata, default=serialize_date)} -->\n\n{processed_content}"
            
            result = ProcessingResult(
                success=True,
                content=processed_content,
                attachments=attachments or [],
                timings={},
                errors=[],
                metadata=frontmatter  # Include frontmatter in result metadata
            )
            self.logger.debug(f"Processing result: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error processing markdown file {file_path}: {str(e)}")
            return ProcessingResult(
                success=False,
                content="",
                attachments=[],
                timings={},
                errors=[str(e)],
                metadata={}
            )
            
    async def handle(self, file_path: Path, context: Dict[str, Any] = None) -> str:
        """Handle a markdown file and its attachments."""
        try:
            self.logger.debug(f"Starting to handle file: {file_path}")
            self.logger.debug(f"Context: {context}")
            
            # Read markdown content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Get output directory from context or use default
            context = context or {}
            output_dir = Path(context.get('output_dir', self.output_dir))
            self.logger.debug(f"Using output directory: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create directory for attachments
            file_stem = context.get('file_stem', file_path.stem)
            output_attachment_dir = output_dir / file_stem
            self.logger.debug(f"Creating attachment directory: {output_attachment_dir}")
            output_attachment_dir.mkdir(parents=True, exist_ok=True)

            # Process attachments if they exist
            attachment_content = []
            attachment_dir = file_path.parent / file_stem
            self.logger.debug(f"Looking for attachments in: {attachment_dir}")
            if attachment_dir.exists() and attachment_dir.is_dir():
                self.logger.debug(f"Found attachment directory: {attachment_dir}")
                # Create temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    for attachment_path in attachment_dir.glob('*'):
                        if attachment_path.is_file():
                            try:
                                self.logger.debug(f"Processing attachment: {attachment_path}")
                                # Copy attachment to temp directory for processing
                                temp_path = temp_dir / attachment_path.name
                                shutil.copy2(attachment_path, temp_path)
                                
                                # Create markdown for attachment
                                markdown = await self._process_attachment(attachment_path, output_attachment_dir)
                                if markdown:
                                    # Create markdown file for attachment
                                    attachment_md_path = output_attachment_dir / f"{attachment_path.stem}.md"
                                    self.logger.debug(f"Writing attachment markdown to: {attachment_md_path}")
                                    attachment_md_path.write_text(markdown)
                                    
                                    # Add link to attachment markdown in main content
                                    rel_md_path = attachment_md_path.relative_to(output_dir)
                                    attachment_content.append(f"- [{attachment_path.name}]({rel_md_path})")
                                    
                            except Exception as e:
                                self.logger.error(f"Error processing attachment {attachment_path}: {str(e)}")
                                attachment_content.append(f"- Error processing {attachment_path.name}: {str(e)}")

            # Add attachment links to content if any were processed
            if attachment_content:
                content += "\n\n## Attachments\n\n" + "\n".join(attachment_content)

            # Write processed content to output file
            output_file = output_dir / f"{file_stem}.md"
            self.logger.debug(f"Writing main content to: {output_file}")
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(content)

            return content
            
        except Exception as e:
            self.logger.error(f"Error handling markdown file {file_path}: {str(e)}")
            return None
    
    async def _process_attachment(self, file_path: Path, output_dir: Path) -> str:
        """Process an attachment file and return markdown content."""
        start_time = time.time()
        markdown = ""
        
        try:
            # Get file info
            file_info = await self.file_info_provider.get_file_info(file_path)
            
            # Create relative path for the attachment
            rel_path = file_path.relative_to(self.input_dir)
            output_path = output_dir / rel_path
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file to output directory
            shutil.copy2(file_path, output_path)
            self.logger.info(f"Copied {file_path} to {output_path}")
            
            # Process based on content type
            if file_info.content_type.startswith('image/'):
                # Get image info and analysis
                image_info = await self.image_converter.get_image_info(file_path, output_path)
                
                # Add TODO comment about image processing
                markdown += "\n//TODO: IMAGE PROCESSING NOT WORKING\n"
                
                if image_info.success:
                    # Add image reference
                    markdown += f"\n![{file_path.name}]({rel_path})\n\n"
                    
                    # Add structured analysis
                    if image_info.description:
                        markdown += f"### Analysis\n\n{image_info.description}\n\n"
                    
                    if image_info.content_type == "screenshot" and image_info.visible_text:
                        markdown += f"### Extracted Text\n\n```\n{image_info.visible_text}\n```\n\n"
                        
                    if image_info.context:
                        for section, content in image_info.context.items():
                            title = section.replace('_', ' ').title()
                            markdown += f"### {title}\n\n{content}\n\n"
                    
                    # Add timing information
                    if image_info.timings:
                        markdown += "### Processing Details\n\n```\n"
                        for operation, timing in image_info.timings.items():
                            if isinstance(timing, (int, float)):
                                markdown += f"{operation}: {timing:.2f}s\n"
                            else:
                                markdown += f"{operation}: {timing}\n"
                        markdown += "```\n\n"
                else:
                    markdown += f"\nError processing image {file_path.name}: {image_info.error}\n\n"
                    
            elif file_info.content_type.startswith('text/'):
                # Handle text files
                try:
                    content = file_path.read_text()
                    markdown += f"\n### {file_path.name}\n\n```\n{content}\n```\n\n"
                except Exception as e:
                    markdown += f"\nError reading text file {file_path.name}: {str(e)}\n\n"
                    
            elif file_info.content_type in ['application/json', 'application/x-json']:
                # Handle JSON files
                try:
                    content = file_path.read_text()
                    markdown += f"\n### {file_path.name}\n\n```json\n{content}\n```\n\n"
                except Exception as e:
                    markdown += f"\nError reading JSON file {file_path.name}: {str(e)}\n\n"
                    
            elif file_info.content_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
                # Handle document files (PDF, Word, Excel)
                markdown += f"\n### {file_path.name}\n\n"
                markdown += f"[Download {file_path.name}]({rel_path})\n\n"
                
                # Add file metadata
                markdown += "#### File Details\n\n"
                markdown += f"- Type: {file_info.content_type}\n"
                markdown += f"- Size: {file_info.size} bytes\n"
                if file_info.metadata:
                    markdown += "- Metadata:\n"
                    for key, value in file_info.metadata.items():
                        markdown += f"  - {key}: {value}\n"
                markdown += "\n"
                
            else:
                # Handle other file types
                markdown += f"\n### {file_path.name}\n\n"
                markdown += f"[Download {file_path.name}]({rel_path})\n\n"
                markdown += f"File type: {file_info.content_type}\n\n"
                
            return markdown
            
        except Exception as e:
            self.logger.error(f"Error processing attachment {file_path}: {str(e)}")
            return f"\nError processing attachment {file_path.name}: {str(e)}\n\n" 
    
    def can_handle(self, file_path: Path, attachments: List[Path] = None) -> bool:
        """Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachment paths
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
        
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate the processing results.
        
        Args:
            result: The processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        if not result.get('success', False):
            return 'error' in result
            
        return (
            isinstance(result.get('content', ''), str) and
            isinstance(result.get('file_path', None), Path) and
            isinstance(result.get('attachments', []), list)
        ) 