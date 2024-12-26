"""Split processor for splitting aggregated markdown into separate files."""

import json
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Generator
from datetime import datetime

from ...core.logging import get_logger
from ...models.processor_result import ProcessorResult
from ..core.base_processor import BaseProcessor
from ...core.file_info_provider import FileInfoProvider
from ...core.metadata_manager import MetadataManager
from ...core.content_analyzer import ContentAnalyzer
from ...core.config.base import ProcessorConfig, PipelineConfig

logger = get_logger(__name__)

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor for splitting markdown files into sections."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.metadata_manager = MetadataManager()
        self.content_analyzer = ContentAnalyzer()
        self.config = processor_config
        self.pipeline_config = pipeline_config
    
    def _split_content_by_metadata(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Split content based on metadata."""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Convert content to lines if it's a string
        if isinstance(content, str):
            content_lines = content.splitlines()
        else:
            content_lines = content
        
        # Get content markers from metadata
        content_markers = metadata.get('content_markers', {})
        
        # Process summary blocks
        summary_blocks = content_markers.get('summary_blocks', [])
        for block in summary_blocks:
            if isinstance(block, dict) and 'content' in block:
                if isinstance(block['content'], list):
                    sections['summary'].extend(block['content'])
                else:
                    sections['summary'].extend(block['content'].splitlines())
            elif isinstance(block, str):
                sections['summary'].extend(block.splitlines())
        
        # Process raw notes blocks
        raw_notes_blocks = content_markers.get('raw_notes_blocks', [])
        for block in raw_notes_blocks:
            if isinstance(block, dict) and 'content' in block:
                if isinstance(block['content'], list):
                    sections['raw_notes'].extend(block['content'])
                else:
                    sections['raw_notes'].extend(block['content'].splitlines())
            elif isinstance(block, str):
                sections['raw_notes'].extend(block.splitlines())
        
        # Process attachment blocks
        attachment_blocks = content_markers.get('attachment_blocks', [])
        for block in attachment_blocks:
            if isinstance(block, dict) and 'content' in block:
                if isinstance(block['content'], list):
                    sections['attachments'].extend(block['content'])
                else:
                    sections['attachments'].extend(block['content'].splitlines())
            elif isinstance(block, str):
                sections['attachments'].extend(block.splitlines())
        
        # If no sections were found in metadata, use content analyzer
        if not any(sections.values()):
            current_block = []
            current_section = None
            
            for line in content_lines:
                # Check for section markers
                if '--==SUMMARY==--' in line:
                    if current_block:
                        if current_section:
                            sections[current_section].extend(current_block)
                        else:
                            # Analyze block to determine section
                            section, _ = self.content_analyzer.suggest_section('\n'.join(current_block))
                            sections[section].extend(current_block)
                    current_section = 'summary'
                    current_block = []
                    continue
                elif '--==RAW NOTES==--' in line or '--==RAW_NOTES==--' in line:
                    if current_block:
                        if current_section:
                            sections[current_section].extend(current_block)
                        else:
                            section, _ = self.content_analyzer.suggest_section('\n'.join(current_block))
                            sections[section].extend(current_block)
                    current_section = 'raw_notes'
                    current_block = []
                    continue
                elif '--==ATTACHMENTS==--' in line:
                    if current_block:
                        if current_section:
                            sections[current_section].extend(current_block)
                        else:
                            section, _ = self.content_analyzer.suggest_section('\n'.join(current_block))
                            sections[section].extend(current_block)
                    current_section = 'attachments'
                    current_block = []
                    continue
                
                current_block.append(line)
            
            # Handle any remaining block
            if current_block:
                if current_section:
                    sections[current_section].extend(current_block)
                else:
                    # Analyze block to determine section
                    section, _ = self.content_analyzer.suggest_section('\n'.join(current_block))
                    sections[section].extend(current_block)
        
        # Ensure all sections exist
        for section in sections:
            if not sections[section]:
                sections[section] = []
        
        return sections
    
    def _split_content_by_markers(self, content: str) -> Dict[str, List[str]]:
        """Split content based on section markers."""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        lines = content.splitlines()
        current_block = []
        current_section = None
        has_markers = False
        
        # Track block context for better content analysis
        block_context = {
            'has_code': False,
            'has_images': False,
            'in_code_block': False,
            'list_depth': 0
        }
        
        for line in lines:
            # Update block context
            if line.startswith('```'):
                block_context['in_code_block'] = not block_context['in_code_block']
                if block_context['in_code_block']:
                    block_context['has_code'] = True
            
            if '![' in line and '](' in line:
                block_context['has_images'] = True
            
            if line.strip().startswith(('- ', '* ', '+ ', '1. ')):
                block_context['list_depth'] += 1
            elif not line.strip():
                block_context['list_depth'] = 0
            
            # Check for section markers
            if '--==SUMMARY==--' in line:
                has_markers = True
                if current_block:
                    if current_section:
                        sections[current_section].extend(current_block)
                    else:
                        # Analyze block with context
                        section = self._analyze_block_with_context(current_block, block_context)
                        sections[section].extend(current_block)
                current_section = 'summary'
                current_block = []
                block_context = {k: False for k in block_context}  # Reset context
                continue
            
            elif '--==RAW NOTES==--' in line or '--==RAW_NOTES==--' in line:
                has_markers = True
                if current_block:
                    if current_section:
                        sections[current_section].extend(current_block)
                    else:
                        section = self._analyze_block_with_context(current_block, block_context)
                        sections[section].extend(current_block)
                current_section = 'raw_notes'
                current_block = []
                block_context = {k: False for k in block_context}
                continue
            
            elif '--==ATTACHMENTS==--' in line:
                has_markers = True
                if current_block:
                    if current_section:
                        sections[current_section].extend(current_block)
                    else:
                        section = self._analyze_block_with_context(current_block, block_context)
                        sections[section].extend(current_block)
                current_section = 'attachments'
                current_block = []
                block_context = {k: False for k in block_context}
                continue
            
            # Add line to current block if we're in a section
            if current_section:
                current_block.append(line)
            else:
                # If no section markers found, analyze content to determine section
                section, confidence = self.content_analyzer.suggest_section(line)
                if confidence < 0.5:  # Low confidence in content analysis
                    current_block.append(line)  # Collect lines for block analysis
                    if len(current_block) >= 5 or (not has_markers and line.strip() == ''):
                        # Analyze accumulated block
                        section = self._analyze_block_with_context(current_block, block_context)
                        sections[section].extend(current_block)
                        current_block = []
                        block_context = {k: False for k in block_context}
                else:
                    sections[section].append(line)
        
        # Handle any remaining block
        if current_block:
            if current_section:
                sections[current_section].extend(current_block)
            else:
                section = self._analyze_block_with_context(current_block, block_context)
                sections[section].extend(current_block)
        
        # If no sections were found, analyze entire content
        if not any(sections.values()):
            section, confidence = self.content_analyzer.suggest_section(content)
            if confidence < 0.5:
                section = 'raw_notes'  # Default to raw notes for uncertain content
            sections[section].extend(lines)
        
        return sections
    
    def _analyze_block_with_context(self, block: List[str], context: Dict[str, bool]) -> str:
        """Analyze a block of content with additional context."""
        content = '\n'.join(block)
        
        # Use content analyzer for initial suggestion
        section, confidence = self.content_analyzer.suggest_section(content)
        
        # Adjust based on context
        if context['has_code'] and confidence < 0.8:
            return 'raw_notes'  # Code usually belongs in raw notes
        
        if context['has_images'] and confidence < 0.8:
            return 'attachments'  # Images usually belong in attachments
        
        if context['list_depth'] > 2 and confidence < 0.8:
            return 'raw_notes'  # Deep lists usually indicate detailed content
        
        return section
    
    def _update_relationships(
        self,
        sections: Dict[str, List[str]],
        metadata: Dict[str, Any]
    ) -> Tuple[Dict[str, List[str]], Dict[str, Any]]:
        """Update relationships in sections and metadata."""
        # Initialize relationships if not present
        if 'relationships' not in metadata:
            metadata['relationships'] = {
                'attachments': [],
                'references': [],
                'dependencies': []
            }
        
        # Track relationships by section
        section_relationships = {
            'summary': {'attachments': [], 'references': [], 'dependencies': []},
            'raw_notes': {'attachments': [], 'references': [], 'dependencies': []},
            'attachments': {'attachments': [], 'references': [], 'dependencies': []}
        }
        
        # Process each section
        for section_name, content in sections.items():
            content_str = '\n'.join(content)
            
            # Find images
            for match in re.finditer(r'!\[(.*?)\]\((.*?)\)', content_str):
                alt_text, path = match.groups()
                relationship = {
                    'type': 'image',
                    'path': path,  # Use path for images
                    'alt_text': alt_text,
                    'source': section_name
                }
                section_relationships[section_name]['attachments'].append(relationship)
            
            # Find document links
            for match in re.finditer(r'\[(.*?)\]\((.*?\.(?:pdf|docx?|xlsx?|csv|txt))\)', content_str):
                text, path = match.groups()
                relationship = {
                    'type': 'document',
                    'target': path,  # Use target for links
                    'text': text,
                    'source': section_name
                }
                section_relationships[section_name]['references'].append(relationship)
            
            # Find other links
            for match in re.finditer(r'\[(.*?)\]\((.*?)\)', content_str):
                text, path = match.groups()
                if not any(ext in path.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.png', '.jpg', '.jpeg', '.gif']):
                    relationship = {
                        'type': 'link',
                        'target': path,  # Use target for links
                        'text': text,
                        'source': section_name
                    }
                    section_relationships[section_name]['references'].append(relationship)
        
        # Update metadata with section-specific relationships
        for section_name, relationships in section_relationships.items():
            metadata[f'section_{section_name}'] = {
                'relationships': relationships
            }
        
        # Update global relationships
        metadata['relationships'] = {
            'attachments': [
                rel for section in section_relationships.values()
                for rel in section['attachments']
            ],
            'references': [
                rel for section in section_relationships.values()
                for rel in section['references']
            ],
            'dependencies': [
                rel for section in section_relationships.values()
                for rel in section['dependencies']
            ]
        }
        
        return sections, metadata
    
    def _read_file_in_chunks(self, file_path: str, chunk_size: int = 1024 * 1024) -> Generator[str, None, None]:
        """Read a file in chunks to handle large files.
        
        Args:
            file_path: Path to file to read
            chunk_size: Size of chunks to read in bytes
            
        Yields:
            File contents in chunks
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    def _parse_metadata(self, content: str) -> Dict[str, Any]:
        """Parse metadata from content.
        
        Args:
            content: Content to parse metadata from
            
        Returns:
            Parsed metadata dictionary
        """
        try:
            # Find metadata comment in first chunk
            metadata_str = ""
            found_start = False
            found_end = False
            
            # If content is a file path, read it in chunks
            if os.path.isfile(content):
                chunks = self._read_file_in_chunks(content)
            else:
                # If content is a string, treat it as a single chunk
                chunks = [content]
                
            for chunk in chunks:
                if not found_start:
                    # Look for metadata start marker
                    start_idx = chunk.find('<!--')
                    if start_idx == -1:
                        continue
                        
                    found_start = True
                    metadata_str = chunk[start_idx + 4:]  # Skip '<!--'
                else:
                    metadata_str += chunk
                    
                # Look for metadata end marker
                end_idx = metadata_str.find('-->')
                if end_idx != -1:
                    found_end = True
                    metadata_str = metadata_str[:end_idx]
                    break
                    
            if not found_start or not found_end:
                self.logger.warning("No metadata found in content")
                return {}
            
            # Clean up metadata string
            metadata_str = metadata_str.strip()
            
            # Handle common JSON issues
            try:
                # First try parsing as is
                return json.loads(metadata_str)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Initial JSON parse failed: {str(e)}")
                
                # Try cleaning up the string
                try:
                    # Remove newlines and extra whitespace
                    metadata_str = re.sub(r'\s+', ' ', metadata_str)
                    
                    # Fix common quote issues
                    metadata_str = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"', r'"\1"', metadata_str)
                    metadata_str = metadata_str.replace("'", '"')
                    
                    # Remove trailing commas
                    metadata_str = re.sub(r',(\s*[}\]])', r'\1', metadata_str)
                    
                    # Ensure property names are quoted
                    metadata_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', metadata_str)
                    
                    # Try parsing again
                    return json.loads(metadata_str)
                except json.JSONDecodeError as e2:
                    self.logger.error(f"Failed to parse cleaned metadata: {str(e2)}")
                    self.logger.error(f"Problematic metadata string: {metadata_str}")
                    return {}
                
        except Exception as e:
            self.logger.error(f"Failed to parse metadata: {str(e)}")
            return {}
    
    async def process(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Process the input files."""
        result = ProcessorResult()
        
        try:
            # Set up paths
            input_dir = input_dir or Path(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE', ''))
            output_dir = output_dir or Path(os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT', ''))
            
            input_file = input_dir / "all_merged_markdown.md"
            
            if not input_file.exists():
                logger.warning(f"Aggregated markdown file not found: {input_file}")
                result.success = True  # Not an error, just no work to do
                return result
            
            logger.debug(f"Found aggregated markdown file: {input_file}")
            
            # Read content and extract metadata
            try:
                content = input_file.read_text(encoding='utf-8')
            except Exception as e:
                error_msg = f"Failed to read input file: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
                return result
            
            # Split content into sections first
            try:
                sections = self._split_content_by_markers(content)
            except ValueError as e:
                error_msg = f"Error splitting content: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
                return result
            except Exception as e:
                error_msg = f"Unexpected error splitting content: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
                return result
            
            # Create output files
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                
                for section_name, section_content in sections.items():
                    output_file = output_dir / f"{section_name}.md"
                    try:
                        # Create section metadata
                        section_metadata = {
                            'document': {
                                'processor': 'ThreeFileSplitProcessor',
                                'version': '1.0',
                                'timestamp': datetime.now().isoformat(),
                                'section': section_name,
                                'source': str(input_file.name)
                            },
                            'relationships': {
                                'attachments': [],
                                'references': [],
                                'dependencies': []
                            }
                        }
                        
                        # Format output content
                        output_content = [
                            f"<!-- {json.dumps(section_metadata, indent=2)} -->",
                            "",  # Empty line after metadata
                            *section_content
                        ]
                        
                        # Write the file
                        output_file.write_text('\n'.join(output_content), encoding='utf-8')
                        result.processed_files.append(output_file)
                    except PermissionError as e:
                        error_msg = f"Permission denied writing to {output_file}: {str(e)}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)
                        result.success = False
                        return result
                    except Exception as e:
                        error_msg = f"Error writing {output_file}: {str(e)}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)
                        result.success = False
                        return result
                
                # Validate that we created all required files
                if not all((output_dir / f"{section}.md").exists() for section in ['summary', 'raw_notes', 'attachments']):
                    error_msg = "Failed to create all required section files"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
                    result.success = False
                    return result
                
                result.success = True
                
            except PermissionError as e:
                error_msg = f"Permission denied creating output directory: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
                return result
            except Exception as e:
                error_msg = f"Error creating output files: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
                return result
            
        except Exception as e:
            error_msg = f"Unexpected error in processor: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            result.success = False
        
        return result