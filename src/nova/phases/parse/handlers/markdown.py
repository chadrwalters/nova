"""Markdown handler for parsing markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.phases.core.base_handler import BaseHandler


class MarkdownHandler(BaseHandler):
    """Markdown handler for parsing markdown files."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize markdown handler.
        
        Args:
            name: Handler name
            options: Handler options
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
        """
        super().__init__(
            name=name,
            options=options,
            timing=timing,
            metrics=metrics,
            monitoring=monitoring,
            console=console
        )
        self.logger = logging.getLogger(__name__)

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if handler can process file, False otherwise
        """
        return file_path.suffix.lower() == '.md'

    async def process(self, file_path: Path, context: Dict[str, Any]) -> HandlerResult:
        """Process markdown file.
        
        Args:
            file_path: Path to file
            context: Processing context
            
        Returns:
            Handler result
            
        Raises:
            ValidationError: If processing fails
        """
        try:
            self.logger.info(f"Processing file: {file_path}")

            # Read file content
            content = file_path.read_text()

            # Parse content
            parsed_content = self._parse_content(content)

            # Write parsed content
            output_file = Path(context['output_file'])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(parsed_content)

            # Also write metadata file
            metadata_file = output_file.with_suffix('.json')
            metadata = {
                'original_file': str(file_path),
                'output_file': str(output_file),
                'handler': self.name,
                'success': True
            }
            metadata_file.write_text(str(metadata))

            return HandlerResult(
                success=True,
                content=parsed_content,
                metadata=metadata
            )

        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)

    def _parse_content(self, content: str) -> str:
        """Parse markdown content.
        
        Args:
            content: Content to parse
            
        Returns:
            Parsed content
        """
        lines = []
        in_code_block = False
        in_frontmatter = False
        frontmatter_lines = []

        # Process content line by line
        for line in content.split('\n'):
            # Handle code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                lines.append(line)
                continue

            # Skip processing if in code block
            if in_code_block:
                lines.append(line)
                continue

            # Handle frontmatter
            if line.strip() == '---':
                if not in_frontmatter and not lines:
                    in_frontmatter = True
                elif in_frontmatter:
                    in_frontmatter = False
                lines.append(line)
                continue

            # Process line
            if in_frontmatter:
                lines.append(line)
            else:
                # Process headers
                if line.strip().startswith('#'):
                    line = self._process_header(line)
                
                # Process links and images
                line = self._process_links(line)
                line = self._process_images(line)
                
                lines.append(line)

        return '\n'.join(lines)

    def _process_header(self, line: str) -> str:
        """Process markdown header.
        
        Args:
            line: Header line
            
        Returns:
            Processed header line
        """
        # Add header ID if not present
        if '{#' not in line:
            header_text = line.lstrip('#').strip()
            header_id = header_text.lower().replace(' ', '-')
            line = f"{line} {{#{header_id}}}"

        return line

    def _process_links(self, line: str) -> str:
        """Process markdown links.
        
        Args:
            line: Line containing links
            
        Returns:
            Processed line
        """
        result = []
        current_pos = 0
        
        while current_pos < len(line):
            # Find next link
            link_start = line.find('[', current_pos)
            if link_start == -1:
                result.append(line[current_pos:])
                break
                
            # Add text before link
            result.append(line[current_pos:link_start])
            
            # Find link parts
            text_end = line.find(']', link_start)
            if text_end == -1:
                result.append(line[link_start:])
                break
                
            url_start = line.find('(', text_end)
            if url_start == -1 or url_start != text_end + 1:
                result.append(line[link_start:text_end + 1])
                current_pos = text_end + 1
                continue
                
            url_end = line.find(')', url_start)
            if url_end == -1:
                result.append(line[link_start:])
                break
                
            # Extract link parts
            text = line[link_start + 1:text_end]
            url = line[url_start + 1:url_end]
            
            # Add title if not present
            if ' "' not in url and "'" not in url:
                url = f'{url} "{text}"'
                
            # Rebuild link
            result.append(f'[{text}]({url})')
            current_pos = url_end + 1
            
        return ''.join(result)

    def _process_images(self, line: str) -> str:
        """Process markdown images.
        
        Args:
            line: Line containing images
            
        Returns:
            Processed line
        """
        result = []
        current_pos = 0
        
        while current_pos < len(line):
            # Find next image
            img_start = line.find('![', current_pos)
            if img_start == -1:
                result.append(line[current_pos:])
                break
                
            # Add text before image
            result.append(line[current_pos:img_start])
            
            # Find image parts
            alt_end = line.find(']', img_start)
            if alt_end == -1:
                result.append(line[img_start:])
                break
                
            url_start = line.find('(', alt_end)
            if url_start == -1 or url_start != alt_end + 1:
                result.append(line[img_start:alt_end + 1])
                current_pos = alt_end + 1
                continue
                
            url_end = line.find(')', url_start)
            if url_end == -1:
                result.append(line[img_start:])
                break
                
            # Extract image parts
            alt = line[img_start + 2:alt_end]
            url = line[url_start + 1:url_end]
            
            # Add title if not present
            if ' "' not in url and "'" not in url:
                url = f'{url} "{alt}"'
                
            # Rebuild image
            result.append(f'![{alt}]({url})')
            current_pos = url_end + 1
            
        return ''.join(result)

    def validate_output(self, result: HandlerResult) -> bool:
        """Validate handler result.
        
        Args:
            result: Handler result
            
        Returns:
            True if result is valid, False otherwise
        """
        return (
            result.success and
            isinstance(result.content, str) and
            isinstance(result.metadata, dict) and
            'output_file' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 