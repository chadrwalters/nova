"""Split phase module."""

import re
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set
import shutil
from collections import defaultdict

from nova.phases.base import Phase
from nova.models.document import DocumentMetadata
from nova.models.links import LinkContext, LinkType
from nova.utils.file_utils import safe_write_file

class SplitPhase(Phase):
    """Split phase of the document processing pipeline."""
    
    # Simple type mapping for organization
    TYPE_MAP = {
        '.docx': 'DOC',
        '.doc': 'DOC',
        '.pdf': 'PDF',
        '.jpg': 'JPG',
        '.jpeg': 'JPG',
        '.heic': 'JPG',
        '.png': 'PNG',
        '.svg': 'DOC',
        '.html': 'DOC',
        '.txt': 'TXT',
        '.json': 'JSON',
        '.xlsx': 'EXCEL',
        '.xls': 'EXCEL',
        '.csv': 'EXCEL',
        '.md': 'DOC'
    }
    
    def __init__(self, pipeline):
        super().__init__(pipeline)
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
        # Extract name
        name = Path(path).stem
        if name.endswith('.summary') or name.endswith('.rawnotes'):
            name = name.rsplit('.', 1)[0]
        
        # If it's a note, use [NOTE:name] format
        if is_note:
            return f"[NOTE:{name}]"
            
        # For attachments, use [ATTACH:TYPE:name] format
        file_type = self._get_file_type(path)
        return f"[ATTACH:{file_type}:{name}]"
        
    def _extract_attachments(self, file_path: Path) -> List[Dict]:
        """Extract attachments from a file's directory.
        
        Args:
            file_path: Path to the file being processed
            
        Returns:
            List of attachment information dictionaries
        """
        attachments = []
        seen_refs = set()
        
        # Get the base name without .summary.md or .rawnotes.md
        base_name = file_path.stem.rsplit('.', 1)[0]
        
        # Check for attachments directory
        attachments_dir = file_path.parent / base_name
        if attachments_dir.exists() and attachments_dir.is_dir():
            for attachment_path in attachments_dir.glob('*.md'):
                if attachment_path.is_file():
                    # Create reference
                    ref = self._make_reference(attachment_path)
                    if ref in seen_refs:
                        continue
                    seen_refs.add(ref)
                    
                    # Get content for context
                    try:
                        content = attachment_path.read_text(encoding='utf-8')
                    except Exception:
                        content = ""
                    
                    # Build attachment info
                    attachment = {
                        "reference": ref,
                        "text": attachment_path.stem,
                        "path": str(attachment_path),
                        "type": self._get_file_type(str(attachment_path)),
                        "section": "attachments",
                        "context": content[:500],  # First 500 chars as context
                        "is_image": False  # All attachments are markdown now
                    }
                    attachments.append(attachment)
                    
        return attachments
        
    def _build_attachments_markdown(self, attachments: List[Dict]) -> str:
        """Build markdown content for attachments file."""
        content = ["# Attachments\n"]
        
        # Group attachments by type
        by_type = defaultdict(list)
        for attachment in attachments:
            by_type[attachment['type']].append(attachment)
            
        # Build sections for each type
        for file_type in sorted(by_type.keys()):
            content.append(f"\n## {file_type} Files\n")
            
            # Add each attachment
            for attachment in sorted(by_type[file_type], key=lambda x: x['text']):
                content.append(f"\n### {attachment['reference']}")
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
        """Process a file through the split phase."""
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version="1.0"
                )
                
            # Read the file content
            content = file_path.read_text(encoding='utf-8')
            
            # Get file title (remove .summary.md or .rawnotes.md)
            title = file_path.stem.rsplit('.', 1)[0]
            
            # Create output files based on input type
            if file_path.name.endswith('.summary.md'):
                # Handle summary file
                summary_path = output_dir / 'Summary.md'
                if not summary_path.exists():
                    with open(summary_path, 'w') as f:
                        f.write("# Summary\n\n")
                
                if content.strip():
                    with open(summary_path, 'a') as f:
                        f.write(f"\n## {title}\n\n")
                        f.write(content.strip())
                        f.write(f"\n\n---\nRaw Notes: {self._make_reference(title, is_note=True)}\n")
                    self._update_section_stats('summary', 'processed')
                else:
                    self._update_section_stats('summary', 'empty')
                    
            elif file_path.name.endswith('.rawnotes.md'):
                # Handle raw notes file
                notes_path = output_dir / 'Raw Notes.md'
                if not notes_path.exists():
                    with open(notes_path, 'w') as f:
                        f.write("# Raw Notes\n\n")
                
                if content.strip():
                    with open(notes_path, 'a') as f:
                        f.write(f"\n## {self._make_reference(title, is_note=True)}\n\n")
                        f.write(content.strip())
                        f.write("\n")
                    self._update_section_stats('raw_notes', 'processed')
                else:
                    self._update_section_stats('raw_notes', 'empty')
                    
            # Extract and process attachments
            attachments = self._extract_attachments(file_path)
            if attachments:
                # Initialize attachments collection if needed
                if not hasattr(self, '_all_attachments'):
                    self._all_attachments = []
                    self._attachments_written = False
                
                # Add new attachments
                self._all_attachments.extend(attachments)
                self._update_section_stats('attachments', 'processed')
            else:
                self._update_section_stats('attachments', 'empty')
                
            # Update metadata
            metadata.processed = True
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error(self.__class__.__name__, str(e))
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
            attachments_content = self._build_attachments_markdown(self._all_attachments)
            if attachments_content:
                safe_write_file(attachments_path, attachments_content)
        
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