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
import re

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
    
    # File type categories
    DOCUMENT_TYPES = {
        'text': {
            'markdown': ['.md', '.markdown'],
            'text': ['.txt', '.text'],
            'code': ['.py', '.js', '.java', '.cpp', '.h', '.c', '.cs', '.html', '.css', '.json', '.yaml', '.yml']
        },
        'office': {
            'word': ['.doc', '.docx'],
            'excel': ['.xls', '.xlsx', '.csv'],
            'powerpoint': ['.ppt', '.pptx'],
            'pdf': ['.pdf']
        },
        'image': {
            'raster': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.bmp'],
            'vector': ['.svg', '.eps', '.ai']
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize markdown handler.
        
        Args:
            config: Configuration dictionary containing:
                analyze_images: Whether to analyze images with OpenAI Vision API
        """
        super().__init__(config)
        self.base_dir = os.path.expandvars(os.environ.get('NOVA_BASE_DIR', ''))
        self.input_dir = os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', ''))
        self.output_dir = os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', ''))
        
        if not all([self.base_dir, self.input_dir, self.output_dir]):
            raise ValueError("Required environment variables not set: NOVA_BASE_DIR, NOVA_INPUT_DIR, NOVA_PHASE_MARKDOWN_PARSE")
            
        self.base_dir = Path(self.base_dir)
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        
        self.image_converter = ImageConverter(analyze_images=config.get('analyze_images', False))
        self.document_converter = DocumentConverter()
        self.logger = get_logger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize file info provider
        self.file_info_provider = FileInfoProvider()
    
    def get_file_type(self, file_path: Path) -> Tuple[str, str]:
        """Get the category and specific type of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (category, specific_type)
        """
        ext = file_path.suffix.lower()
        
        for category, type_dict in self.DOCUMENT_TYPES.items():
            for specific_type, extensions in type_dict.items():
                if ext in extensions:
                    return category, specific_type
        
        return 'unknown', 'unknown'
    
    async def _process_attachment(self, file_path: Path, output_dir: Path) -> Optional[str]:
        """Process an attachment file.
        
        Args:
            file_path: Path to the attachment
            output_dir: Directory to save processed files
            
        Returns:
            Optional[str]: Markdown content for the attachment
        """
        try:
            # Get file type
            category, specific_type = self.get_file_type(file_path)
            
            # Handle by category
            if category == 'image':
                # For now, just add a TODO comment and maintain the reference
                return f"<!-- TODO: Image '{file_path.name}' needs to be processed -->\n![{file_path.stem}]({file_path.name})"
                
            elif category == 'office':
                # Convert office document to markdown
                result = await self.document_converter.convert_to_markdown(file_path, output_dir)
                if result.success:
                    # Save the markdown content to a file
                    output_file = output_dir / f"{file_path.stem}.md"
                    async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                        await f.write(result.content)
                    # Return a reference to the markdown file
                    return f"[{file_path.stem}]({file_path.stem}.md)"
                else:
                    return f"Error converting document {file_path.name}: {result.error}"
                    
            elif category == 'text':
                # For text files, convert directly to markdown
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                # Save as markdown
                output_file = output_dir / f"{file_path.stem}.md"
                async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                    await f.write(f"```{specific_type}\n{content}\n```")
                # Return a reference to the markdown file
                return f"[{file_path.stem}]({file_path.stem}.md)"
                
            else:
                # For unknown types, add a comment and reference
                return f"<!-- TODO: Unsupported file type '{file_path.suffix}' -->\n[{file_path.name}]({file_path.name})"
                
        except Exception as e:
            self.logger.error(f"Error processing attachment {file_path}: {str(e)}")
            return f"Error processing {file_path.name}: {str(e)}"
    
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
                
                # Group attachments by type
                attachments_by_type = {}
                for attachment_path in attachment_dir.glob('*'):
                    if attachment_path.is_file():
                        # Skip .json files
                        if attachment_path.suffix.lower() == '.json':
                            continue
                            
                        category, specific_type = self.get_file_type(attachment_path)
                        if category not in attachments_by_type:
                            attachments_by_type[category] = {}
                        if specific_type not in attachments_by_type[category]:
                            attachments_by_type[category][specific_type] = []
                        attachments_by_type[category][specific_type].append(attachment_path)
                
                # Process each type of attachment
                for category, type_dict in sorted(attachments_by_type.items()):
                    if type_dict:
                        attachment_content.append(f"\n### {category.title()} Files\n")
                        for specific_type, files in sorted(type_dict.items()):
                            for file_path in sorted(files):
                                try:
                                    # Process the attachment
                                    markdown = await self._process_attachment(file_path, output_attachment_dir)
                                    if markdown:
                                        # For images, update the path to be relative to the attachment directory
                                        if category == 'image':
                                            # Handle HEIC files
                                            if file_path.suffix.lower() in ['.heic', '.heif']:
                                                markdown = markdown.replace(
                                                    f"]({file_path.stem}.jpg)",
                                                    f"]({file_stem}/{file_path.stem}.jpg)"
                                                )
                                            else:
                                                markdown = markdown.replace(
                                                    f"]({file_path.name})",
                                                    f"]({file_stem}/{file_path.name})"
                                                )
                                        attachment_content.append(markdown)
                                except Exception as e:
                                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                                    attachment_content.append(f"Error processing {file_path.name}: {str(e)}")

            # Add attachment links to content if any were processed
            if attachment_content:
                content += "\n\n## Attachments\n" + "\n".join(attachment_content)

            # Write processed content to output file
            output_file = output_dir / f"{file_stem}.md"
            self.logger.debug(f"Writing main content to: {output_file}")
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error handling file {file_path}: {str(e)}")
            raise
    
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

    def _classify_document_type(self, content: str) -> str:
        """Classify document type based on content analysis."""
        # Check for summary indicators
        summary_indicators = ['summary:', 'overview:', 'key points:', 'highlights:']
        if any(indicator in content.lower() for indicator in summary_indicators):
            return 'summary'
            
        # Check for raw notes indicators
        raw_notes_indicators = ['notes:', 'log:', 'journal:', 'raw notes:']
        if any(indicator in content.lower() for indicator in raw_notes_indicators):
            return 'raw_notes'
            
        # Check for attachment indicators
        if '![' in content or '[download]' in content.lower():
            return 'attachment'
            
        return 'unknown'

    def _extract_references(self, content: str) -> List[Dict[str, str]]:
        """Extract markdown links and references from content."""
        references = []
        
        # Match markdown links [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            references.append({
                'type': 'link',
                'text': match.group(1),
                'url': match.group(2)
            })
            
        # Match image references ![alt](url)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, content):
            references.append({
                'type': 'image',
                'alt': match.group(1),
                'url': match.group(2)
            })
            
        return references

    def _identify_summary_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Identify summary blocks in content."""
        blocks = []
        current_block = None
        
        for line in content.split('\n'):
            if any(indicator in line.lower() for indicator in ['summary:', 'overview:', 'key points:']):
                if current_block:
                    blocks.append(current_block)
                current_block = {'type': 'summary', 'content': [], 'start_line': len(blocks) + 1}
            elif current_block and line.strip() and not any(indicator in line.lower() for indicator in ['raw notes:', 'attachments:']):
                current_block['content'].append(line)
            elif current_block and not line.strip():
                if current_block['content']:
                    blocks.append(current_block)
                current_block = None
                
        if current_block and current_block['content']:
            blocks.append(current_block)
            
        return blocks

    def _identify_raw_notes_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Identify raw notes blocks in content."""
        blocks = []
        current_block = None
        
        for line in content.split('\n'):
            if any(indicator in line.lower() for indicator in ['raw notes:', 'log:', 'journal:']):
                if current_block:
                    blocks.append(current_block)
                current_block = {'type': 'raw_notes', 'content': [], 'start_line': len(blocks) + 1}
            elif current_block and line.strip() and not any(indicator in line.lower() for indicator in ['summary:', 'attachments:']):
                current_block['content'].append(line)
            elif current_block and not line.strip():
                if current_block['content']:
                    blocks.append(current_block)
                current_block = None
                
        if current_block and current_block['content']:
            blocks.append(current_block)
            
        return blocks

    def _identify_attachment_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Identify attachment blocks in content."""
        blocks = []
        current_block = None
        
        for line in content.split('\n'):
            if '![' in line or '[download]' in line.lower():
                blocks.append({
                    'type': 'attachment',
                    'content': line,
                    'line_number': len(blocks) + 1
                })
                
        return blocks 

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
            
            # Check if this is a markdown file
            category, specific_type = self.get_file_type(file_path)
            if category != 'text' or specific_type != 'markdown':
                raise ValueError(f"Not a markdown file: {file_path}")
            
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
            
            # Process the markdown file and its attachments
            processed_content = await self.handle(file_path, {
                'output_dir': output_dir,
                'file_stem': file_stem,
                **context
            })
            
            # Parse frontmatter from processed content
            frontmatter, content = parse_frontmatter(processed_content)
            
            # Enhanced metadata structure
            metadata = {
                'document': {
                    'file': str(file_path),
                    'processor': 'MarkdownHandler',
                    'version': '1.0',
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'markdown',
                    'frontmatter': frontmatter,
                },
                'structure': {
                    'root_document': True,  # Indicates if this is a root document
                    'parent_document': context.get('parent_document'),  # Link to parent if this is a sub-document
                    'sequence_number': context.get('sequence_number', 1),  # Order in document sequence
                    'document_type': self._classify_document_type(content),  # summary, raw_notes, or attachment
                },
                'relationships': {
                    'attachments': [str(a) for a in (attachments or [])],
                    'references': self._extract_references(content),  # Extract markdown links and references
                    'dependencies': context.get('dependencies', []),  # Files this document depends on
                },
                'assembly': {
                    'phase': 'parse',
                    'group': context.get('group'),  # Group identifier for related documents
                    'merge_priority': context.get('merge_priority', 50),  # Priority for merging (0-100)
                    'preserve_headers': context.get('preserve_headers', True),
                },
                'content_markers': {
                    'summary_blocks': self._identify_summary_blocks(content),
                    'raw_notes_blocks': self._identify_raw_notes_blocks(content),
                    'attachment_blocks': self._identify_attachment_blocks(content),
                }
            }
            
            # Add metadata as HTML comment
            final_content = f"<!-- {json.dumps(metadata, default=serialize_date)} -->\n\n{processed_content}"
            
            # Write final content to output file
            output_file = output_dir / f"{file_stem}.md"
            self.logger.debug(f"Writing final content to: {output_file}")
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(final_content)
            
            return ProcessingResult(
                success=True,
                content=final_content,
                attachments=attachments or [],
                timings={},
                errors=[],
                metadata=metadata
            )
            
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