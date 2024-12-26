"""Processor for aggregating markdown files."""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from nova.core.logging import get_logger
from nova.core.pipeline.base import BaseProcessor
from nova.models.processor_result import ProcessorResult
from nova.core.file_info_provider import FileInfoProvider
from nova.core.metadata_manager import MetadataManager
from nova.core.config.base import ProcessorConfig, PipelineConfig

logger = get_logger(__name__)

class MarkdownAggregateProcessor(BaseProcessor):
    """Processor for aggregating markdown files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.metadata_manager = MetadataManager()
        self.config = processor_config
        self.pipeline_config = pipeline_config
    
    def _update_relationships(
        self,
        content: List[str],
        metadata: Dict[str, Any],
        file_path: Path,
        input_dir: Path,
        file_map: Dict[str, int]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Update relationships and references in content.
        
        Args:
            content: Content lines to update
            metadata: Metadata containing relationship information
            file_path: Current file path
            input_dir: Input directory path
            file_map: Mapping of files to their sequence numbers
            
        Returns:
            Tuple of (updated content lines, updated metadata)
        """
        updated_content = []
        updated_metadata = metadata.copy()
        
        # Initialize relationship tracking
        if 'relationships' not in updated_metadata:
            updated_metadata['relationships'] = {
                'attachments': [],
                'references': [],
                'dependencies': []
            }
        
        # Get file's relative directory for path updates
        rel_dir = file_path.parent.relative_to(input_dir)
        
        # Regular expressions for finding links and images
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        image_pattern = r'!\[([^\]]+)\]\(([^)]+)\)'
        
        for line in content:
            updated_line = line
            
            # Update image references
            for match in re.finditer(image_pattern, line):
                alt_text, img_path = match.groups()
                img_path = Path(img_path)
                
                # Skip URLs
                if not any(img_path.as_posix().startswith(p) for p in ['http://', 'https://', '/']):
                    # Calculate new path relative to output
                    if img_path.is_absolute():
                        new_path = img_path.relative_to(input_dir)
                    else:
                        new_path = rel_dir / img_path
                    
                    # Update the line with new path
                    updated_line = updated_line.replace(
                        f'![{alt_text}]({img_path})',
                        f'![{alt_text}]({new_path})'
                    )
                    
                    # Track attachment relationship
                    attachment_info = {
                        'type': 'image',
                        'source': str(file_path.relative_to(input_dir)),
                        'path': str(new_path),
                        'alt_text': alt_text
                    }
                    if attachment_info not in updated_metadata['relationships']['attachments']:
                        updated_metadata['relationships']['attachments'].append(attachment_info)
            
            # Update markdown links
            for match in re.finditer(link_pattern, line):
                text, link_path = match.groups()
                link_path = Path(link_path)
                
                # Skip URLs and anchors
                if not any(str(link_path).startswith(p) for p in ['http://', 'https://', '#', '/']):
                    # Calculate new path relative to output
                    if link_path.is_absolute():
                        new_path = link_path.relative_to(input_dir)
                    else:
                        new_path = rel_dir / link_path
                    
                    # Update the line with new path
                    updated_line = updated_line.replace(
                        f'[{text}]({link_path})',
                        f'[{text}]({new_path})'
                    )
                    
                    # Track reference relationship
                    reference_info = {
                        'type': 'link',
                        'source': str(file_path.relative_to(input_dir)),
                        'target': str(new_path),
                        'text': text
                    }
                    if reference_info not in updated_metadata['relationships']['references']:
                        updated_metadata['relationships']['references'].append(reference_info)
                    
                    # Track dependency if it's a markdown file
                    if link_path.suffix.lower() in ['.md', '.markdown']:
                        dependency_info = {
                            'source': str(file_path.relative_to(input_dir)),
                            'target': str(new_path),
                            'type': 'markdown_link'
                        }
                        if dependency_info not in updated_metadata['relationships']['dependencies']:
                            updated_metadata['relationships']['dependencies'].append(dependency_info)
            
            updated_content.append(updated_line)
        
        return updated_content, updated_metadata
    
    def _organize_content(
        self,
        content: str,
        metadata: Dict[str, Any],
        file_path: Path
    ) -> Dict[str, List[str]]:
        """Organize content into sections based on metadata.
        
        Args:
            content: Raw content to organize
            metadata: Metadata containing section information
            file_path: Path to the source file
            
        Returns:
            Dict mapping section types to their content lines
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Get content markers from metadata
        content_markers = metadata.get('content_markers', {})
        
        # Split content into lines
        content_lines = content.splitlines()
        
        # Track current position in content
        current_pos = 0
        
        # Process summary blocks
        summary_blocks = content_markers.get('summary_blocks', [])
        for block in summary_blocks:
            if isinstance(block, dict) and 'content' in block:
                sections['summary'].extend(block['content'])
            elif isinstance(block, str):
                sections['summary'].append(block)
        
        # Process raw notes blocks
        raw_notes_blocks = content_markers.get('raw_notes_blocks', [])
        for block in raw_notes_blocks:
            if isinstance(block, dict) and 'content' in block:
                sections['raw_notes'].extend(block['content'])
            elif isinstance(block, str):
                sections['raw_notes'].append(block)
        
        # Process attachment blocks
        attachment_blocks = content_markers.get('attachment_blocks', [])
        for block in attachment_blocks:
            if isinstance(block, dict) and 'content' in block:
                sections['attachments'].extend(block['content'])
            elif isinstance(block, str):
                sections['attachments'].append(block)
        
        # If no sections were found in metadata, try to analyze content
        if not any(sections.values()):
            current_section = None
            for line in content_lines:
                # Check for section indicators
                lower_line = line.lower()
                if any(indicator in lower_line for indicator in ['summary:', 'overview:', 'key points:']):
                    current_section = 'summary'
                    continue
                elif any(indicator in lower_line for indicator in ['raw notes:', 'notes:', 'log:', 'journal:']):
                    current_section = 'raw_notes'
                    continue
                elif any(indicator in lower_line for indicator in ['attachments:', 'files:', 'resources:']):
                    current_section = 'attachments'
                    continue
                elif '![' in line or '[' in line and '](' in line:  # Image or link
                    sections['attachments'].append(line)
                    continue
                
                # Add line to current section if set
                if current_section:
                    sections[current_section].append(line)
                else:
                    # Default to raw_notes if no section is identified
                    sections['raw_notes'].append(line)
        
        # Add section markers
        for section_name, section_content in sections.items():
            if section_content:
                section_content.insert(0, f"--=={section_name.upper()}==--")
        
        return sections
    
    async def process(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Process markdown files in the input directory.
        
        Args:
            input_dir: Directory containing consolidated markdown files
            output_dir: Directory to write aggregated file to
            context: Processing context
            
        Returns:
            ProcessorResult containing success/failure and any errors
        """
        result = ProcessorResult()
        context = context or {}
        
        try:
            # Use provided directories or get from environment
            input_dir = input_dir or Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE')))
            output_dir = output_dir or Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE')))
            
            # Ensure directories exist
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get file info provider from context or create new one
            file_info_provider = context.get('file_info_provider') or FileInfoProvider()
            
            # Find all markdown files
            input_files = list(input_dir.rglob("*.md"))
            
            if not input_files:
                logger.warning(f"No markdown files found in {input_dir}")
                # Create empty output file with basic metadata
                empty_metadata = {
                    'document': {
                        'processor': 'MarkdownAggregateProcessor',
                        'version': '1.0',
                        'timestamp': datetime.now().isoformat(),
                    },
                    'structure': {
                        'files': [],
                        'section_order': ['summary', 'raw_notes', 'attachments']
                    },
                    'relationships': {'attachments': [], 'references': [], 'dependencies': []},
                    'content_markers': {'summary_blocks': [], 'raw_notes_blocks': [], 'attachment_blocks': []}
                }
                output_file = output_dir / "all_merged_markdown.md"
                output_file.write_text(self.metadata_manager.serialize_metadata(empty_metadata), encoding='utf-8')
                result.success = True
                return result
            
            # Sort files by date if available
            def get_file_date(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    metadata, _ = self.metadata_manager.extract_metadata(content)
                    if 'document' in metadata and 'timestamp' in metadata['document']:
                        return datetime.fromisoformat(metadata['document']['timestamp'])
                except:
                    pass
                return file_path.stat().st_mtime
            
            input_files.sort(key=get_file_date)
            
            # Create file map for relationship updates
            file_map = {
                str(f.relative_to(input_dir)): i 
                for i, f in enumerate(input_files)
            }
            
            # Initialize metadata list and organized sections
            metadata_list = []
            organized_sections = {
                'summary': [],
                'raw_notes': [],
                'attachments': []
            }
            
            # Process each file
            for file_path in input_files:
                try:
                    # Get file info
                    file_info = await file_info_provider.get_file_info(file_path)
                    
                    # Skip non-markdown files
                    if not (file_info.content_type == 'text/markdown' or file_path.suffix.lower() == '.md'):
                        continue
                    
                    # Read content and extract metadata
                    content = file_path.read_text(encoding='utf-8')
                    metadata, content = self.metadata_manager.extract_metadata(content)
                    
                    # Update file path in metadata
                    if 'document' not in metadata:
                        metadata['document'] = {}
                    metadata['document']['file'] = str(file_path.relative_to(input_dir))
                    
                    # Organize content into sections
                    sections = self._organize_content(content, metadata, file_path)
                    
                    # Update relationships for each section
                    for section_name, section_content in sections.items():
                        updated_content, updated_metadata = self._update_relationships(
                            section_content,
                            metadata,
                            file_path,
                            input_dir,
                            file_map
                        )
                        sections[section_name] = updated_content
                        metadata = updated_metadata
                    
                    # Add to metadata list
                    metadata_list.append(metadata)
                    
                    # Add file markers and append to organized sections
                    rel_path = file_path.relative_to(input_dir)
                    for section_name, section_content in sections.items():
                        if section_content:
                            organized_sections[section_name].extend([
                                f"\n<!-- START_FILE: {rel_path} -->",
                                *section_content,
                                f"<!-- END_FILE: {rel_path} -->",
                                "\n---\n"
                            ])
                    
                    result.processed_files.append(file_path)
                    
                except Exception as e:
                    error_msg = f"Failed to aggregate {file_path}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
            
            if any(organized_sections.values()):
                # Merge all metadata
                merged_metadata = self.metadata_manager.merge_metadata(metadata_list)
                
                # Validate merged metadata
                validation_errors = self.metadata_manager.validate_metadata(merged_metadata)
                if validation_errors:
                    for error in validation_errors:
                        logger.warning(f"Metadata validation warning: {error}")
                
                # Create final content with merged metadata and organized sections
                final_content = [self.metadata_manager.serialize_metadata(merged_metadata)]
                
                # Add sections in the correct order
                section_order = merged_metadata['structure']['section_order']
                for section_name in section_order:
                    if organized_sections[section_name]:
                        final_content.extend(organized_sections[section_name])
                
                # Write aggregated content
                output_file = output_dir / "all_merged_markdown.md"
                output_file.write_text('\n'.join(final_content), encoding='utf-8')
                
                result.success = True
            else:
                error_msg = "No content to aggregate"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.success = False
            
        except Exception as e:
            error_msg = f"Aggregation phase failed: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            result.success = False
        
        return result