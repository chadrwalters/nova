from markdown_it import MarkdownIt
from pathlib import Path
from typing import Dict, Any, Optional
import re
import aiofiles
import asyncio
from ..core.exceptions import ProcessingError, ValidationError, MarkdownError
from ..core.config import NovaConfig
from ..core.logging import get_logger
import yaml

logger = get_logger(__name__)

class MarkdownProcessor:
    def __init__(self, config: NovaConfig):
        self.config = config
        self.md = self._configure_markdown_it(config)
        
    def _configure_markdown_it(self, config: NovaConfig) -> MarkdownIt:
        """Configure markdown-it with plugins and options."""
        md = MarkdownIt('commonmark', {
            'typographer': config.markdown.options.typographer,
            'linkify': config.markdown.options.linkify,
            'breaks': config.markdown.options.breaks,
            'html': True
        })
        
        # Add custom horizontal rule renderer
        def render_hr(tokens, idx, options, env):
            return '\n\n<div style="border-top: 1px solid black; margin: 1em 0;"></div>\n\n'
            
        # Override default hr renderer
        md.add_render_rule('hr', render_hr)
        
        # Try to load plugins safely
        try:
            from mdit_py_plugins.front_matter import front_matter_plugin
            md.use(front_matter_plugin)
        except ImportError:
            logger.warning("front_matter_plugin_not_available")
            
        try:
            from mdit_py_plugins.footnote import footnote_plugin
            md.use(footnote_plugin)
        except ImportError:
            logger.warning("footnote_plugin_not_available")
            
        try:
            from mdit_py_plugins.tasklists import tasklists_plugin
            md.use(tasklists_plugin)
        except ImportError:
            logger.warning("tasklists_plugin_not_available")
        
        # Enable core features
        md.enable(['table', 'strikethrough'])
        
        return md

    async def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Dict containing:
                - content: Rendered markdown content
                - metadata: Extracted metadata
                - path: Original file path
                
        Raises:
            ProcessingError: If file processing fails
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            metadata = await self._extract_metadata(content)
            # Remove metadata block from content if present
            if metadata:
                content = await self._remove_metadata_block(content)
                
            return {
                'content': self.md.render(content),
                'metadata': metadata,
                'path': file_path
            }
        except Exception as e:
            raise ProcessingError(f"Failed to process markdown file {file_path}: {str(e)}")

    async def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML metadata from markdown content.
        
        Metadata should be at the start of the file between --- markers:
        ---
        title: My Document
        author: John Doe
        date: 2024-01-01
        ---
        """
        metadata_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(metadata_pattern, content, re.DOTALL)
        
        if not match:
            return {}
            
        try:
            metadata_str = match.group(1)
            # Run YAML parsing in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, yaml.safe_load, metadata_str)
            return metadata or {}
        except Exception as e:
            # Log warning but don't fail processing
            logger.warning("metadata_extraction_failed", error=str(e))
            return {}

    async def _remove_metadata_block(self, content: str) -> str:
        """Remove metadata block from content if present."""
        metadata_pattern = r'^---\s*\n.*?\n---\s*\n'
        return re.sub(metadata_pattern, '', content, flags=re.DOTALL) 

    async def validate_markdown(self, content: str) -> None:
        """Validate markdown content."""
        try:
            # Log the first few lines for debugging
            preview = '\n'.join(content.split('\n')[:5])
            logger.debug("validating_markdown",
                        preview=preview)
            
            # Check for basic structure
            if not content.strip():
                raise ValidationError("Empty markdown content")
                
            # Parse with markdown-it to check structure
            md = MarkdownIt()
            # Enable core features only for validation
            md.enable(['table', 'strikethrough'])
            
            # Run parsing in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            tokens = await loop.run_in_executor(None, md.parse, content)
            
            # Track opening/closing tags
            tag_stack = []
            block_level = 0
            
            for token in tokens:
                if token.type == 'html_block' or token.type == 'html_inline':
                    if not self.config.security.sanitize_html:
                        continue
                        
                if token.nesting > 0:  # Opening tag
                    tag_stack.append(token.tag)
                    block_level += 1
                elif token.nesting < 0:  # Closing tag
                    if not tag_stack or token.tag != tag_stack[-1]:
                        logger.warning("unbalanced_tag",
                                   expected=tag_stack[-1] if tag_stack else None,
                                   found=token.tag,
                                   stack=tag_stack,
                                   level=block_level)
                        if self.config.processing.error_tolerance == 'strict':
                            raise ValidationError(f"Unbalanced markdown elements found")
                        continue
                    tag_stack.pop()
                    block_level -= 1
            
            # Check for any remaining open tags
            if tag_stack:
                logger.warning("unclosed_tags", tags=tag_stack)
                if self.config.processing.error_tolerance == 'strict':
                    raise ValidationError("Unclosed markdown tags found")
                    
        except Exception as e:
            if not isinstance(e, ValidationError):
                logger.error("markdown_validation_failed", error=str(e))
                if self.config.processing.error_tolerance == 'strict':
                    raise ValidationError(f"Markdown validation failed: {str(e)}")
            elif self.config.processing.error_tolerance == 'strict':
                raise