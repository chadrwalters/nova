"""Split phase implementation."""

import logging
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict

from nova.config.manager import ConfigManager
from nova.core.metadata import FileMetadata, DocumentMetadata
from nova.phases.base import Phase
from nova.handlers.registry import HandlerRegistry

logger = logging.getLogger(__name__)

class SplitPhase(Phase):
    """Split phase of the document processing pipeline."""
    
    # Simple type mapping for organization
    TYPE_MAP = {
        '.docx': 'DOC',
        '.doc': 'DOC',
        '.pdf': 'PDF',
        '.jpg': 'IMAGE',
        '.jpeg': 'IMAGE',
        '.heic': 'IMAGE',
        '.png': 'IMAGE',
        '.svg': 'IMAGE',
        '.html': 'DOC',
        '.txt': 'TXT',
        '.json': 'JSON',
        '.xlsx': 'EXCEL',
        '.xls': 'EXCEL',
        '.csv': 'EXCEL',
        '.md': 'DOC'
    }
    
    def __init__(self, config: ConfigManager, pipeline=None):
        """Initialize the split phase."""
        super().__init__("split", config, pipeline)
        self.handler_registry = HandlerRegistry(config)
        self.stats = defaultdict(lambda: {"processed": 0, "skipped": 0, "errors": 0})
        
        self.section_stats = {
            'summary': {'processed': 0, 'empty': 0, 'error': 0},
            'raw_notes': {'processed': 0, 'empty': 0, 'error': 0},
            'attachments': {'processed': 0, 'empty': 0, 'error': 0}
        }
        
    def _get_file_type(self, path: str) -> str:
        """Get standardized file type from path."""
        ext = Path(path).suffix.lower()
        return self.TYPE_MAP.get(ext, 'OTHER')
        
    def _make_reference(self, path: str, is_note: bool = False) -> str:
        """Create a reference marker for a path.
        
        Args:
            path: Path to create reference for
            is_note: Whether this is a note reference
            
        Returns:
            Reference marker string
        """
        # Extract name without any extensions
        name = Path(path).stem
        # Remove .parsed extension if present
        if name.endswith('.parsed'):
            name = name[:-7]
        
        # If it's a note, use [NOTE:name] format
        if is_note:
            return f"[NOTE:{name}]"
            
        # For attachments, use [ATTACH:TYPE:name] format
        file_type = self._get_file_type(path)
        return f"[ATTACH:{file_type}:{name}]"
        
    def _extract_attachments(self, file_path: Path) -> List[Dict]:
        """Extract attachments from a file."""
        attachments = []
        seen_refs = set()
        
        # Function to process attachments from a directory
        def process_directory(dir_path: Path, relative_path: str = ""):
            if dir_path.exists() and dir_path.is_dir():
                # Process all files in this directory
                for attachment_path in dir_path.glob('*.*'):
                    if attachment_path.is_file():
                        # Get file type from extension
                        file_type = self._get_file_type(str(attachment_path))
                        
                        # Create reference using just the base name
                        base_name = attachment_path.stem
                        if base_name.endswith('.parsed'):
                            # Remove .parsed extension
                            base_name = base_name[:-7]  # Remove '.parsed'
                        else:
                            # For non-parsed files, just use the stem
                            base_name = Path(base_name).stem
                            
                        ref = f"[ATTACH:{file_type}:{base_name}]"
                        
                        if ref in seen_refs:
                            continue
                        seen_refs.add(ref)
                        
                        # Get content for context
                        try:
                            if file_type in ['IMAGE', 'PDF', 'EXCEL']:
                                content = f"Binary file: {attachment_path.name}"
                            else:
                                content = attachment_path.read_text(encoding='utf-8')
                        except Exception:
                            content = f"Binary file: {attachment_path.name}"
                        
                        # Build attachment info
                        attachment = {
                            "reference": ref,
                            "text": attachment_path.stem,
                            "path": str(attachment_path),
                            "type": file_type,
                            "section": "attachments",
                            "context": content[:500] if len(content) > 500 else content,
                            "is_image": file_type == 'IMAGE',
                            "directory": relative_path  # Store directory path
                        }
                        attachments.append(attachment)
                
                # Process subdirectories
                for subdir in dir_path.glob('*/'):
                    if subdir.is_dir():
                        process_directory(subdir, str(Path(relative_path) / subdir.name))
        
        # Process the main directory
        process_directory(file_path)
        
        return attachments
        
    def _build_attachments_markdown(self, attachments: List[Dict]) -> str:
        """Build markdown content for attachments file."""
        content = ["# Attachments\n"]
        
        # Group attachments by directory first, then by type
        by_directory = defaultdict(lambda: defaultdict(list))
        for attachment in attachments:
            directory = attachment.get('directory', '')
            file_type = attachment['type']
            by_directory[directory][file_type].append(attachment)
            
        # Build sections for each directory
        for directory in sorted(by_directory.keys()):
            if directory:
                content.append(f"\n## Directory: {directory}\n")
            
            # Build sections for each type within the directory
            for file_type in sorted(by_directory[directory].keys()):
                content.append(f"\n### {file_type} Files\n")
                
                # Add each attachment
                for attachment in sorted(by_directory[directory][file_type], key=lambda x: x['text']):
                    content.append(f"\n#### {attachment['reference']}")
                    if attachment['text']:
                        content.append(f"\n**{attachment['text']}**")
                    if attachment['context']:
                        content.append(f"\n{attachment['context'].strip()}")
                    content.append("\n")
                
        return "\n".join(content)

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None
    ) -> Optional[DocumentMetadata]:
        """Process a file in the split phase."""
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0"
                )
            
            # Get base name without extensions
            base_name = file_path.stem
            if base_name.endswith('.summary'):
                base_name = base_name[:-8]  # Remove '.summary'
            elif base_name.endswith('.rawnotes'):
                base_name = base_name[:-9]  # Remove '.rawnotes'
            
            # Look for related files in the same directory
            summary_file = file_path.parent / f"{base_name}.summary.md"
            raw_notes_file = file_path.parent / f"{base_name}.rawnotes.md"
            
            # Get relative path from input directory
            try:
                # First get the original input file path from metadata
                if metadata and metadata.file_path:
                    original_path = Path(metadata.file_path)
                    rel_path = original_path.relative_to(self.config.input_dir)
                else:
                    # Fallback to using the current file path relative to disassemble dir
                    disassemble_dir = self.pipeline.config.processing_dir / "phases" / "disassemble"
                    rel_path = file_path.relative_to(disassemble_dir)
            except ValueError:
                # If not under input_dir or disassemble_dir, use just the filename
                rel_path = Path(base_name)
            
            # Create output directory preserving relative path
            split_phase_dir = self.pipeline.get_phase_output_dir('split')
            output_subdir = split_phase_dir / rel_path.parent
            output_subdir.mkdir(parents=True, exist_ok=True)
            
            # Track sections for each output file
            summary_sections = []
            raw_notes_sections = []
            attachments = {}
            
            # Process summary file if it exists
            if summary_file and summary_file.exists():
                summary_content = summary_file.read_text(encoding='utf-8')
                if summary_content.strip():
                    summary_sections.append(summary_content)
            
            # Process raw notes file if it exists
            if raw_notes_file and raw_notes_file.exists():
                raw_notes_content = raw_notes_file.read_text(encoding='utf-8')
                if raw_notes_content.strip():
                    raw_notes_sections.append(raw_notes_content)
            
            # Get parent directory name for attachments
            parent_dir = file_path.parent.name
            if parent_dir not in attachments:
                attachments[parent_dir] = []
            
            # Get attachments from parse phase
            parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
            if parse_dir.exists():
                # Look for files in the same directory as the input file
                input_dir = file_path.parent
                for file_path in input_dir.glob('*.*'):
                    if file_path.is_file() and not file_path.name.endswith(('.summary.md', '.rawnotes.md')):
                        # Get file type from extension
                        file_ext = file_path.suffix.lower()
                        file_type = self.TYPE_MAP.get(file_ext, 'OTHER')
                        
                        # Create attachment info
                        attachment = {
                            'path': str(file_path),
                            'id': file_path.stem,
                            'type': file_type,
                            'content': f"Binary file: {file_path.name}" if file_type in ['IMAGE', 'PDF', 'EXCEL'] else file_path.read_text(encoding='utf-8')
                        }
                        attachments[parent_dir].append(attachment)
            
            # Write or append to consolidated files
            if summary_sections:
                summary_file = output_subdir / "Summary.md"
                # Read existing content if file exists
                existing_content = summary_file.read_text(encoding='utf-8') if summary_file.exists() else ""
                # Append new content with a separator
                full_content = existing_content + ("\n\n" if existing_content else "") + '\n\n'.join(summary_sections)
                summary_file.write_text(full_content, encoding='utf-8')
                metadata.add_output_file(summary_file)
            
            if raw_notes_sections:
                raw_notes_file = output_subdir / "Raw Notes.md"
                # Read existing content if file exists
                existing_content = raw_notes_file.read_text(encoding='utf-8') if raw_notes_file.exists() else ""
                # Append new content with a separator
                full_content = existing_content + ("\n\n" if existing_content else "") + '\n\n'.join(raw_notes_sections)
                raw_notes_file.write_text(full_content, encoding='utf-8')
                metadata.add_output_file(raw_notes_file)
            
            if attachments:
                # Store attachments for finalize phase
                if not hasattr(self, '_all_attachments'):
                    self._all_attachments = {}
                self._all_attachments.update(attachments)
                
                # Write directory-specific attachments file
                attachments_file = output_subdir / "Attachments.md"
                self._write_attachments_file(attachments, output_subdir)
                if attachments_file.exists():
                    metadata.add_output_file(attachments_file)
                
                # Write consolidated attachments file in the split phase directory
                consolidated_attachments_file = split_phase_dir / "Attachments.md"
                self._write_attachments_file(self._all_attachments, split_phase_dir)
                metadata.add_output_file(consolidated_attachments_file)
            
            metadata.processed = True
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to split file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
            return metadata
            
    def _update_section_stats(self, section: str, status: str) -> None:
        """Update section processing statistics."""
        if section in self.section_stats and status in self.section_stats[section]:
            self.section_stats[section][status] += 1
            
    def finalize(self) -> None:
        """Finalize the split phase."""
        # Write attachments file if we have any
        if hasattr(self, '_all_attachments') and self._all_attachments:
            attachments_path = self.pipeline.config.processing_dir / "phases" / "split" / "Attachments.md"
            # Ensure directory exists
            attachments_path.parent.mkdir(parents=True, exist_ok=True)
            # Write attachments file
            attachments_file = self._write_attachments_file(self._all_attachments, attachments_path.parent)
        
        # Log any failed files
        failed_files = self.pipeline.state['split']['failed_files']
        if failed_files:
            logger.warning(f"Failed to process {len(failed_files)} files:")
            for file_path in failed_files:
                logger.warning(f"  - {file_path}")
        
        # Log empty sections only as warnings
        for section, stats in self.section_stats.items():
            if stats['empty'] > 0:
                logger.warning(f"Found {stats['empty']} empty {section} sections")

    def _write_attachments_file(self, attachments: Dict[str, List[Dict]], output_dir: Path) -> None:
        """Write attachments file.
        
        Args:
            attachments: Dict mapping parent directory names to lists of attachment info
            output_dir: Output directory
        """
        try:
            # Create output file path - ensure it's in the correct directory
            attachments_file = output_dir / "Attachments.md"
            
            # Create directory if it doesn't exist
            attachments_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Build content
            content = ["# Attachments\n"]
            
            # Process each parent directory's attachments
            for parent_dir, attachment_list in sorted(attachments.items()):
                if attachment_list:
                    content.append(f"\n## {parent_dir}\n")
                    
                    # Group attachments by type
                    by_type = defaultdict(list)
                    for attachment in attachment_list:
                        # Get attachment type from file extension
                        file_path = attachment.get('path', '')
                        file_type = self._get_file_type(file_path)
                        by_type[file_type].append(attachment)
                    
                    # Process each type
                    for file_type in sorted(by_type.keys()):
                        content.append(f"\n### {file_type} Files\n")
                        
                        # Process each attachment of this type
                        for attachment in sorted(by_type[file_type], key=lambda x: x.get('id', '')):
                            # Get base name without any extensions
                            file_path = Path(attachment.get('path', ''))
                            base_name = file_path.stem
                            while '.' in base_name:
                                base_name = Path(base_name).stem
                            
                            # Create standardized reference
                            ref = f"[ATTACH:{file_type}:{base_name}]"
                            content.append(f"\n#### {ref}")
                            
                            # Add title if available
                            if 'text' in attachment:
                                content.append(f"\n**{attachment['text']}**")
                            elif 'id' in attachment:
                                content.append(f"\n**{attachment['id']}**")
                            
                            # Add content preview if available
                            if 'content' in attachment:
                                preview = attachment['content']
                                if len(preview) > 500:
                                    preview = preview[:500] + "..."
                                content.append(f"\n{preview.strip()}")
                            
                            content.append("\n")
            
            # Write content
            content_str = "\n".join(content)
            attachments_file.write_text(content_str, encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to write attachments file: {str(e)}")