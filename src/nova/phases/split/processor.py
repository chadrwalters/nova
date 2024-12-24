"""Three-file split processor for markdown content.

This module provides functionality for splitting markdown content into three separate files:
1. summary.md - Contains high-level overview and key points
2. raw_notes.md - Contains detailed notes and chronological entries
3. attachments.md - Contains embedded content and file attachments
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any

from ...core.pipeline.base import BaseProcessor
from ...core.config import ProcessorConfig, PipelineConfig
from ...core.errors import ProcessingError
from ...core.utils.logging import get_logger

logger = get_logger(__name__)

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor that splits content into three files: summary, raw notes, and attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.logger = get_logger(self.__class__.__name__)
        
    def _setup(self) -> None:
        """Setup processor requirements."""
        # Get configuration
        config = self.config.options.get('components', {}).get('three_file_split_processor', {}).get('config', {})
        
        if not config:
            raise ProcessingError("Missing three_file_split_processor configuration")
            
        # Setup output files
        self.output_files = config.get('output_files', {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        })
        
        # Setup section markers
        self.section_markers = config.get('section_markers', {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW_NOTES==--',
            'attachments': '--==ATTACHMENTS==--'
        })
        
        # Setup attachment markers
        self.attachment_markers = config.get('attachment_markers', {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        })
        
        # Setup content type rules
        self.content_type_rules = config.get('content_type_rules', {
            'summary': [
                'Contains high-level overviews',
                'Contains key insights and decisions',
                'Contains structured content'
            ],
            'raw_notes': [
                'Contains detailed notes and logs',
                'Contains chronological entries',
                'Contains unstructured content'
            ],
            'attachments': [
                'Contains file references',
                'Contains embedded content',
                'Contains metadata'
            ]
        })
        
        # Setup content preservation
        self.content_preservation = config.get('content_preservation', {
            'validate_input_size': True,
            'validate_output_size': True,
            'track_content_markers': True,
            'verify_section_integrity': True
        })
        
        # Setup other options
        self.cross_linking = config.get('cross_linking', True)
        self.preserve_headers = config.get('preserve_headers', True)
        
        # Initialize stats
        self.stats.update({
            'summary_size': 0,
            'raw_notes_size': 0,
            'attachments_size': 0,
            'files_processed': 0,
            'errors': 0,
            'warnings': 0
        })
        
        # Setup output directories
        self._setup_directories()
        
    def _setup_directories(self) -> None:
        """Create required directories."""
        # Output directory will be provided by the pipeline manager
        # No need to create additional subdirectories
        pass

    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process content and split into three files.
        
        Args:
            input_path: Path to input file or directory
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
                raise ProcessingError(f"Input path not found: {input_path}")
            
            # Handle directory
            if input_path.is_dir():
                results = []
                for file_path in input_path.glob('**/*.md'):
                    try:
                        # Get relative path to maintain directory structure
                        rel_path = file_path.relative_to(input_path)
                        out_dir = output_path / rel_path.parent
                        
                        # Process file
                        result = self._process_file(file_path, out_dir)
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
            self._handle_error(e, {
                'input_path': str(input_path),
                'output_path': str(output_path)
            })
            return {
                'error': str(e),
                'stats': self.stats
            }
            
    def _process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process a single file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output directory
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        if not input_path.exists():
            raise ProcessingError(f"Input file not found: {input_path}")
            
        content = input_path.read_text(encoding='utf-8')
        
        # Get output paths
        output_files = {
            'summary': output_path / self.output_files['summary'],
            'raw_notes': output_path / self.output_files['raw_notes'],
            'attachments': output_path / self.output_files['attachments']
        }
        
        # Ensure output directories exist
        for path in output_files.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        
        # Split content into sections
        sections = self._split_content(content)
        
        # Write sections to files
        for name, path in output_files.items():
            path.write_text(sections.get(name, ''), encoding='utf-8')
            self.stats[f'{name}_size'] += len(sections.get(name, ''))
        
        self.stats['files_processed'] += 1
        
        return {
            'input_path': str(input_path),
            'output_files': {k: str(v) for k, v in output_files.items()},
            'sections': {k: len(v) for k, v in sections.items()},
            'status': 'success'
        }

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
        """Split content into sections based on markers.
        
        Args:
            content: Content to split
            
        Returns:
            Dictionary of section name to content
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Extract attachment blocks first
        content, attachments = self._extract_attachment_blocks(content)
        
        # Split remaining content by section markers
        current_section = 'raw_notes'  # Default section
        lines = content.split('\n')
        
        for line in lines:
            # Check for section markers
            if line.strip() == self.section_markers['summary']:
                current_section = 'summary'
                continue
            elif line.strip() == self.section_markers['raw_notes']:
                current_section = 'raw_notes'
                continue
            elif line.strip() == self.section_markers['attachments']:
                current_section = 'attachments'
                continue
                
            # Add line to current section
            sections[current_section].append(line)
        
        # Add attachment blocks to attachments section
        for attachment in attachments:
            sections['attachments'].extend([
                '',
                self.attachment_markers['start'].format(filename=attachment['filename']),
                *attachment['content'],
                self.attachment_markers['end']
            ])
        
        # Convert lists to strings
        return {
            name: '\n'.join(lines) for name, lines in sections.items()
        }