"""Split phase of the Nova pipeline."""
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict

from nova.config.manager import ConfigManager
from nova.handlers.registry import HandlerRegistry
from nova.phases.base import Phase
from nova.core.metadata import FileMetadata, DocumentMetadata
from nova.models.links import LinkContext, LinkType
from nova.utils.file_utils import safe_write_file

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
        """Initialize the split phase.
        
        Args:
            config: Configuration manager
            pipeline: Optional pipeline instance
        """
        super().__init__(config, pipeline)
        self.handler_registry = HandlerRegistry(config)
        
        # Set up debug logging
        self.logger.setLevel(logging.DEBUG)
        
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
        """Process a file in the split phase.
        
        Args:
            file_path: Path to file.
            output_dir: Output directory.
            metadata: Optional document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0"
                )
            
            # Get all disassembled files
            disassemble_dir = self.pipeline.config.processing_dir / "phases" / "disassemble"
            if not disassemble_dir.exists():
                self.logger.error("Disassemble directory does not exist")
                return metadata
            
            # Track sections for each output file
            summary_sections = []
            raw_notes_sections = []
            attachments = {}
            
            # Process each disassembled file
            for file in disassemble_dir.rglob("*.summary.md"):
                # Read summary content
                summary_content = file.read_text(encoding='utf-8')
                if summary_content.strip():
                    summary_sections.append(summary_content)
                
                # Check for raw notes
                raw_notes_file = file.parent / f"{file.stem.replace('.summary', '')}.rawnotes.md"
                if raw_notes_file.exists():
                    raw_notes_content = raw_notes_file.read_text(encoding='utf-8')
                    if raw_notes_content.strip():
                        raw_notes_sections.append(raw_notes_content)
                
                # Get parent directory name for attachments
                parent_dir = file.parent.name
                if parent_dir not in attachments:
                    attachments[parent_dir] = []
                
                # Get attachments from pipeline state
                if 'attachments' in self.pipeline.state['disassemble']:
                    if parent_dir in self.pipeline.state['disassemble']['attachments']:
                        # Copy attachments and ensure they have IDs
                        for attachment in self.pipeline.state['disassemble']['attachments'][parent_dir]:
                            attachment_copy = attachment.copy()
                            if 'id' not in attachment_copy:
                                # Use file name as fallback ID
                                attachment_copy['id'] = Path(attachment_copy['path']).stem
                            attachments[parent_dir].append(attachment_copy)
            
            # Get attachments from parse phase
            parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
            if parse_dir.exists():
                # First, get attachments from pipeline state
                if 'attachments' in self.pipeline.state['parse']:
                    for parent_dir, attachment_list in self.pipeline.state['parse']['attachments'].items():
                        if parent_dir not in attachments:
                            attachments[parent_dir] = []
                        for attachment in attachment_list:
                            # Create a copy of the attachment info
                            attachment_copy = attachment.copy()
                            # Get file type from extension
                            file_ext = Path(attachment['path']).suffix.lower()
                            file_type = self.TYPE_MAP.get(file_ext, 'OTHER')
                            attachment_copy['type'] = file_type
                            # Read content if not already present
                            if not attachment_copy.get('content'):
                                try:
                                    if file_type in ['IMAGE', 'PDF', 'EXCEL']:
                                        attachment_copy['content'] = f"Binary file: {Path(attachment['path']).name}"
                                    else:
                                        attachment_copy['content'] = Path(attachment['path']).read_text(encoding='utf-8')
                                except Exception:
                                    attachment_copy['content'] = f"Binary file: {Path(attachment['path']).name}"
                            attachments[parent_dir].append(attachment_copy)
                
                # Then, scan for any parsed files that might have been missed
                for file in parse_dir.rglob("*.parsed.md"):
                    # Only process files in subdirectories
                    if len(file.relative_to(parse_dir).parts) > 1:
                        parent_dir = file.parent.name
                        if parent_dir not in attachments:
                            attachments[parent_dir] = []
                        
                        # Get original file name without .parsed.md extension
                        original_name = file.stem[:-7] if file.stem.endswith('.parsed') else file.stem
                        
                        # Get original file extension from the original name
                        original_ext = Path(original_name).suffix.lower()
                        file_type = self.TYPE_MAP.get(original_ext, 'OTHER')
                        
                        # Read content
                        try:
                            content = file.read_text(encoding='utf-8')
                        except Exception:
                            content = f"Binary file: {file.name}"
                        
                        # Create attachment info with original name as ID
                        attachments[parent_dir].append({
                            'path': str(file),
                            'type': file_type,
                            'content': content,
                            'id': original_name + original_ext,  # Keep the extension
                            'original_name': original_name  # Store original name for reference
                        })
            
            # Write consolidated files
            if summary_sections:
                summary_file = output_dir / "Summary.md"
                summary_file.write_text('\n\n'.join(summary_sections), encoding='utf-8')
                metadata.add_output_file(summary_file)
            
            if raw_notes_sections:
                raw_notes_file = output_dir / "Raw Notes.md"
                raw_notes_file.write_text('\n\n'.join(raw_notes_sections), encoding='utf-8')
                metadata.add_output_file(raw_notes_file)
            
            if attachments:
                # Store attachments for finalize phase
                self._all_attachments = attachments
                # Write attachments file
                attachments_file = self._write_attachments_file(attachments, output_dir)
                if attachments_file and attachments_file.exists():
                    metadata.add_output_file(attachments_file)
            
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
            if attachments_file and attachments_file.exists():
                self.logger.info(f"Successfully wrote attachments file: {attachments_file}")
        
        # Add section stats to pipeline state
        self.pipeline.state['split']['section_stats'] = self.section_stats
        self.logger.info("Split phase completed")
        self.logger.info(f"Section stats: {self.section_stats}")
        
        # Log any failed files
        failed_files = self.pipeline.state['split']['failed_files']
        if failed_files:
            self.logger.warning(f"Failed to process {len(failed_files)} files:")
            for file_path in failed_files:
                self.logger.warning(f"  - {file_path}")
        
        # Log empty sections
        for section, stats in self.section_stats.items():
            if stats['empty'] > 0:
                self.logger.warning(f"Found {stats['empty']} empty {section} sections")

    def _write_attachments_file(self, attachments: Dict[str, List[Dict]], output_dir: Path) -> Optional[Path]:
        """Write consolidated attachments file.
        
        Args:
            attachments: Dict mapping parent directory names to lists of attachment info
            output_dir: Output directory
            
        Returns:
            Path to the attachments file if successful, None otherwise
        """
        try:
            # Create output file paths
            split_attachments_file = self.pipeline.config.processing_dir / "phases" / "split" / "Attachments.md"
            output_attachments_file = output_dir / "Attachments.md"
            
            # Create directories if they don't exist
            split_attachments_file.parent.mkdir(parents=True, exist_ok=True)
            output_attachments_file.parent.mkdir(parents=True, exist_ok=True)
            
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
                            # Create standardized reference using id if available
                            if 'id' in attachment:
                                # Get base name without .parsed extension
                                base_name = attachment['id']
                                if base_name.endswith('.parsed'):
                                    base_name = base_name[:-7]
                                # Remove file extension and keep only the base name
                                base_name = Path(base_name).stem
                                # Keep the original base name with spaces
                                ref = f"[ATTACH:{file_type}:{base_name}]"
                            else:
                                # Get base name without extension for the reference
                                file_path = attachment.get('path', '')
                                base_name = Path(file_path).stem
                                if base_name.endswith('.parsed'):
                                    base_name = base_name[:-7]
                                # Remove any remaining extensions
                                base_name = Path(base_name).stem
                                ref = f"[ATTACH:{file_type}:{base_name}]"
                            content.append(f"\n#### {ref}")
                            
                            # Add title if available
                            if 'text' in attachment:
                                content.append(f"\n**{attachment['text']}**")
                            
                            # Add content preview if available
                            if 'content' in attachment:
                                preview = attachment['content']
                                if len(preview) > 500:
                                    preview = preview[:500] + "..."
                                content.append(f"\n{preview.strip()}")
                            
                            content.append("\n")
            
            # Write content to both locations
            content_str = "\n".join(content)
            
            # Write to split phase directory
            try:
                split_attachments_file.write_text(content_str, encoding='utf-8')
            except Exception as e:
                self.logger.error(f"Failed to write split phase attachments file: {str(e)}")
            
            # Write to output directory
            try:
                output_attachments_file.write_text(content_str, encoding='utf-8')
            except Exception as e:
                self.logger.error(f"Failed to write output attachments file: {str(e)}")
            
            # Return the split phase file path for validation
            return split_attachments_file if split_attachments_file.exists() else output_attachments_file
            
        except Exception as e:
            self.logger.error(f"Failed to write attachments file: {str(e)}")
            return None