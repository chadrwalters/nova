"""Markdown parse processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
import markdown
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ...core.pipeline.base import BaseProcessor
from ...core.config import ProcessorConfig, PipelineConfig
from ...core.errors import ProcessingError
from ...core.utils.logging import get_logger
from ...core.handlers.content_converters import ContentConverterFactory

logger = get_logger(__name__)

class EmbedHandlingConfig(BaseModel):
    """Configuration for embedded content handling."""
    enabled: bool = Field(default=True, description="Whether to process embedded content")
    max_depth: int = Field(default=5, description="Maximum embedding depth")
    allow_external: bool = Field(default=False, description="Allow embedding files outside base directory")

class MarkdownConfig(BaseModel):
    """Configuration for markdown processor."""
    enabled: bool = Field(default=True, description="Whether to process markdown files")
    embed_handling: EmbedHandlingConfig = Field(
        default_factory=EmbedHandlingConfig,
        description="Configuration for embedded content handling"
    )

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.logger = get_logger(self.__class__.__name__)
        self.paths = pipeline_config.paths
        
    def _setup(self) -> None:
        """Setup processor requirements."""
        # Get configuration
        config = self.config.options.get('components', {}).get('markdown_processor', {}).get('config', {})
        
        if not config:
            raise ProcessingError("Missing markdown_processor configuration")
            
        # Parse configuration
        self.config = MarkdownConfig(**config)
            
        # Setup markdown parser
        self.parser = markdown.Markdown(
            extensions=['extra', 'meta', 'toc', 'tables', 'fenced_code']
        )
        
        # Setup content converter
        self.converter = ContentConverterFactory.create_converter('markdown')
        
        # Initialize stats
        self.stats.update({
            'files_processed': 0,
            'errors': 0,
            'warnings': 0
        })

    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process markdown file or directory.
        
        Args:
            input_path: Path to markdown file or directory
            output_path: Path to output directory
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Handle directory
            if input_path.is_dir():
                results = []
                for file_path in input_path.glob('**/*.md'):
                    try:
                        # Get relative path to maintain directory structure
                        rel_path = file_path.relative_to(input_path)
                        out_file = output_path / rel_path
                        
                        # Process file
                        result = self._process_file(file_path, out_file)
                        results.append(result)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process {file_path}: {str(e)}")
                        self.stats['errors'] += 1
                        results.append({
                            'input_path': str(file_path),
                            'error': str(e)
                        })
                
                return {
                    'input_path': str(input_path),
                    'output_path': str(output_path),
                    'files': results,
                    'stats': self.stats
                }
            
            # Handle single file
            return self._process_file(input_path, output_path)
            
        except Exception as e:
            context = {
                'input_path': str(input_path),
                'output_path': str(output_path)
            }
            self._handle_error(e, context)
            return {
                'error': str(e),
                'stats': self.stats
            }
            
    def _process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process a single markdown file.
        
        Args:
            input_path: Path to markdown file
            output_path: Path to output file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        if not input_path.exists():
            raise ProcessingError(f"Input file not found: {input_path}")
            
        content = input_path.read_text(encoding='utf-8')
        
        # Get output path
        output_file = self._get_output_path(str(input_path), str(output_path))
        
        # Process content
        processed_content = self._process_content(content, input_path)
        
        # Write output file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(processed_content, encoding='utf-8')
        
        self.stats['files_processed'] += 1
        
        return {
            'input_path': str(input_path),
            'output_path': str(output_file),
            'status': 'success'
        }

    def _process_content(self, content: str, file_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to source file
            
        Returns:
            Processed content
        """
        # Reset parser to avoid metadata accumulation
        self.parser.reset()
        
        # Process embedded content first
        if isinstance(self.config, MarkdownConfig) and self.config.embed_handling.enabled:
            content = self._process_embedded_content(content, file_path)
        
        # Extract metadata if present
        self.parser.convert(content)
        metadata = getattr(self.parser, 'Meta', {})
        
        # Add metadata back as YAML front matter if present
        if metadata:
            metadata_lines = ['---']
            for key, values in metadata.items():
                if len(values) == 1:
                    metadata_lines.append(f"{key}: {values[0]}")
                else:
                    metadata_lines.append(f"{key}:")
                    for value in values:
                        metadata_lines.append(f"  - {value}")
            metadata_lines.append('---\n')
            content = '\n'.join(metadata_lines) + content
        
        return content

    def _process_embedded_content(self, content: str, file_path: Path, depth: int = 0) -> str:
        """Process embedded content in markdown.
        
        Args:
            content: Markdown content
            file_path: Path to source file
            depth: Current embedding depth
            
        Returns:
            Content with embedded content processed
            
        Raises:
            ProcessingError: If embedding fails
        """
        if not isinstance(self.config, MarkdownConfig):
            return content
            
        if depth >= self.config.embed_handling.max_depth:
            self.logger.warning(f"Maximum embedding depth reached in {file_path}")
            return content
        
        def process_link(match: re.Match) -> str:
            """Process a markdown link that might be marked for embedding."""
            before = match.group(1)  # Text before the link
            link_text = match.group(2)  # Link text
            link_url = match.group(3)  # Link URL
            after = match.group(4) if len(match.groups()) > 3 else ""  # Text after the link
            
            # Check if this link is marked for embedding
            embed_match = re.search(r'<!--\s*(\{.*?"embed":\s*"?true"?.*?\})\s*-->', after)
            if not embed_match:
                return match.group(0)  # Return original if not marked for embedding
            
            try:
                # URL decode the link URL
                from urllib.parse import unquote
                link_url = unquote(link_url)
                
                embed_file = Path(link_url)
                if not embed_file.is_absolute():
                    # Create attachments subdirectory based on markdown filename
                    attachments_dir = file_path.parent / file_path.stem
                    embed_file = attachments_dir / embed_file.name
                
                if not embed_file.exists():
                    raise ProcessingError(f"Embedded file not found: {embed_file}")
                
                if not self.config.embed_handling.allow_external and not self._is_within_base_dir(embed_file):
                    raise ProcessingError(f"External file embedding not allowed: {embed_file}")
                
                # Get converter for file type
                ext = embed_file.suffix.lower().lstrip('.')
                converter = ContentConverterFactory.create_converter(ext)
                content, metadata = converter.convert(embed_file)
                
                # Process embedded markdown recursively
                if embed_file.suffix.lower() in ['.md', '.markdown']:
                    content = self._process_embedded_content(content, embed_file, depth + 1)
                
                # Add markers around embedded content with relative path
                rel_path = embed_file.relative_to(file_path.parent)
                return f"{before}\n--==ATTACHMENT_BLOCK: {rel_path}==--\n{content}\n--==ATTACHMENT_BLOCK_END==--\n"
                
            except Exception as e:
                self.logger.error(f"Failed to embed file {link_url}: {str(e)}")
                return f"{before}[Error embedding {link_url}: {str(e)}]"
        
        # Find markdown links followed by HTML comments with embed:true
        # This pattern matches:
        # 1. Any text before the link (captured)
        # 2. The link text in brackets (captured)
        # 3. The URL in parentheses (captured)
        # 4. Optional HTML comment after (captured)
        pattern = r'([^!]|^)\[([^\]]+)\]\(([^)]+)\)((?:<!--.*?-->)?)'
        content = re.sub(pattern, process_link, content)
        
        return content.rstrip()

    def _is_within_base_dir(self, file_path: Path) -> bool:
        """Check if file is within base directory.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is within base directory
        """
        try:
            file_path.relative_to(self.paths.base_dir)
            return True
        except ValueError:
            return False