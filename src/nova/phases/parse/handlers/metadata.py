"""Metadata handler for parsing markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from nova.core.errors import ValidationError
from nova.core.models.result import HandlerResult
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.console.logger import ConsoleLogger
from nova.phases.core.base_handler import BaseHandler


class MetadataHandler(BaseHandler):
    """Metadata handler for parsing markdown files."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        monitoring: Optional[MonitoringManager] = None,
        console: Optional[ConsoleLogger] = None
    ):
        """Initialize metadata handler.
        
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

            # Extract metadata
            metadata = self._extract_metadata(content)

            # Write metadata to file
            output_dir = Path(context['output_dir'])
            metadata_file = output_dir / f"{file_path.stem}_metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            metadata_file.write_text(str(metadata))

            return HandlerResult(
                success=True,
                content=content,
                metadata=metadata
            )

        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content.
        
        Args:
            content: Content to extract metadata from
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'frontmatter': {},
            'headers': [],
            'links': [],
            'images': [],
            'code_blocks': [],
            'statistics': {
                'total_lines': 0,
                'total_headers': 0,
                'total_links': 0,
                'total_images': 0,
                'total_code_blocks': 0
            }
        }

        # Process content line by line
        in_frontmatter = False
        in_code_block = False
        current_code_block = {
            'language': '',
            'content': []
        }

        for line in content.split('\n'):
            metadata['statistics']['total_lines'] += 1

            # Handle frontmatter
            if line.strip() == '---':
                if not in_frontmatter and metadata['statistics']['total_lines'] == 1:
                    in_frontmatter = True
                    continue
                elif in_frontmatter:
                    in_frontmatter = False
                    continue

            if in_frontmatter:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata['frontmatter'][key.strip()] = value.strip()
                continue

            # Handle code blocks
            if line.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    current_code_block['language'] = line[3:].strip()
                else:
                    in_code_block = False
                    metadata['code_blocks'].append(current_code_block)
                    metadata['statistics']['total_code_blocks'] += 1
                    current_code_block = {
                        'language': '',
                        'content': []
                    }
                continue

            if in_code_block:
                current_code_block['content'].append(line)
                continue

            # Handle headers
            if line.startswith('#'):
                header = {
                    'level': len(line) - len(line.lstrip('#')),
                    'text': line.lstrip('#').strip()
                }
                metadata['headers'].append(header)
                metadata['statistics']['total_headers'] += 1

            # Handle links
            if '[' in line and '](' in line:
                start = 0
                while '[' in line[start:] and '](' in line[start:]:
                    link_start = line.find('[', start)
                    link_mid = line.find('](', link_start)
                    link_end = line.find(')', link_mid)
                    if link_end == -1:
                        break

                    link = {
                        'text': line[link_start+1:link_mid],
                        'url': line[link_mid+2:link_end]
                    }
                    metadata['links'].append(link)
                    metadata['statistics']['total_links'] += 1
                    start = link_end + 1

            # Handle images
            if '![' in line and '](' in line:
                start = 0
                while '![' in line[start:] and '](' in line[start:]:
                    img_start = line.find('![', start)
                    img_mid = line.find('](', img_start)
                    img_end = line.find(')', img_mid)
                    if img_end == -1:
                        break

                    image = {
                        'alt': line[img_start+2:img_mid],
                        'src': line[img_mid+2:img_end]
                    }
                    metadata['images'].append(image)
                    metadata['statistics']['total_images'] += 1
                    start = img_end + 1

        return metadata

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
            'frontmatter' in result.metadata and
            'headers' in result.metadata and
            'links' in result.metadata and
            'images' in result.metadata and
            'code_blocks' in result.metadata and
            'statistics' in result.metadata
        )

    async def cleanup(self):
        """Clean up handler resources."""
        pass 