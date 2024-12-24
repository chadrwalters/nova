"""Markdown aggregate processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re

from ...core.pipeline.base import BaseProcessor
from ...core.config import ProcessorConfig, PipelineConfig
from ...core.errors import ProcessingError
from ...core.utils.logging import get_logger
from ...core.handlers.content_converters import ContentConverterFactory

logger = get_logger(__name__)

class AggregateProcessor(BaseProcessor):
    """Processor that aggregates markdown files into a single file."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        
        # Get configuration
        config = self.config.options.get('components', {}).get('aggregate_processor', {}).get('config', {})
        
        if not config:
            self.logger.error("Missing aggregate_processor configuration")
            raise ProcessingError("Missing aggregate_processor configuration")
            
        # Setup output filename
        self.output_filename = config.get('output_filename', 'all_merged_markdown.md')
        
        # Setup content converter
        self.converter = ContentConverterFactory.create_converter('markdown')
        
        # Initialize stats
        self.stats = {
            'files_processed': 0,
            'total_size': 0,
            'errors': 0,
            'warnings': 0
        }

    def _setup(self) -> None:
        """Setup processor requirements."""
        # No special setup needed for aggregation
        pass

    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process input files and aggregate content.
        
        Args:
            input_path: Path to input directory
            output_path: Path to output directory
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                raise ProcessingError(f"Input path does not exist: {input_path}")
            
            # Get output file path
            output_file = output_path / self.output_filename
            
            # Initialize sections
            summary_content = ["# Aggregated Markdown\n\n"]
            raw_notes_content = ["# Raw Notes\n\n"]
            attachments_content = ["# Attachments\n\n"]
            
            # Process each input file
            for file_path in input_path.glob('**/*.md'):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Extract sections
                    sections = self._extract_sections(content)
                    
                    # Add content to appropriate sections
                    if sections['summary']:
                        summary_content.extend(sections['summary'])
                    if sections['raw_notes']:
                        raw_notes_content.extend(sections['raw_notes'])
                    if sections['attachments']:
                        attachments_content.extend(sections['attachments'])
                        
                    self.stats['files_processed'] += 1
                    self.stats['total_size'] += len(content)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {file_path}: {str(e)}")
                    self.stats['errors'] += 1
                    continue
            
            # Combine sections with separators
            output_content = (
                '--==SUMMARY==--\n\n' +
                '\n'.join(summary_content) + '\n\n' +
                '--==RAW_NOTES==--\n\n' +
                '\n'.join(raw_notes_content) + '\n\n' +
                '--==ATTACHMENTS==--\n\n' +
                '\n'.join(attachments_content)
            )
            
            # Write output file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(output_content, encoding='utf-8')
            
            return {
                'input_path': str(input_path),
                'output_path': str(output_file),
                'stats': self.stats,
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate content: {str(e)}")
            self.stats['errors'] += 1
            return {
                'error': str(e),
                'stats': self.stats
            }

    def _extract_sections(self, content: str) -> Dict[str, List[str]]:
        """Extract content sections.
        
        Args:
            content: Content to extract sections from
            
        Returns:
            Dictionary containing sections
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Split content into lines
        lines = content.split('\n')
        current_section = 'raw_notes'  # Default section
        buffer = []
        
        for line in lines:
            # Check for section markers
            if '--==SUMMARY==--' in line:
                if buffer:
                    sections[current_section].append('\n'.join(buffer))
                buffer = []
                current_section = 'summary'
                continue
            elif '--==RAW NOTES==--' in line:
                if buffer:
                    sections[current_section].append('\n'.join(buffer))
                buffer = []
                current_section = 'raw_notes'
                continue
            elif '--==ATTACHMENT_BLOCK:' in line:
                if buffer:
                    sections[current_section].append('\n'.join(buffer))
                buffer = []
                current_section = 'attachments'
                buffer.append(line)
                continue
            elif '--==ATTACHMENT_BLOCK_END==--' in line:
                buffer.append(line)
                sections['attachments'].append('\n'.join(buffer))
                buffer = []
                current_section = 'raw_notes'
                continue
            
            buffer.append(line)
        
        # Add final buffer
        if buffer:
            sections[current_section].append('\n'.join(buffer))
        
        return sections