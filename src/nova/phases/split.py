"""Split phase module."""

import re
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote
import shutil

from nova.phases.base import Phase
from nova.models.document import DocumentMetadata
from nova.models.links import LinkContext, LinkType
from nova.utils.file_utils import safe_write_file

class SplitPhase(Phase):
    """Split phase of the document processing pipeline."""
    
    # File type to identifier type mapping
    TYPE_MAP = {
        '.jpg': 'JPG',
        '.jpeg': 'JPG',
        '.png': 'PNG',
        '.pdf': 'PDF',
        '.doc': 'DOC',
        '.docx': 'DOC',
        '.txt': 'TXT',
        '.json': 'JSON',
        '.csv': 'CSV',
        '.xlsx': 'EXCEL',
        '.xls': 'EXCEL',
        '.html': 'HTML',
        '.heic': 'IMG'
    }
    
    attachment_pattern = re.compile(
        r"""
        (?:
            (?:\*\s*[^:]*:?\s*)?          # Optional bullet point and type prefix
            (?:
                \[(?P<text>[^\]]*)\]       # [text] for regular links
                |
                \!                         # ! for image links
            )
            \((?P<url>[^)]*?)\)           # (url)
            (?:\s*<!--\s*(?P<metadata>\{[^}]*\})\s*-->)?  # optional metadata
        )
        """,
        re.VERBOSE | re.MULTILINE | re.DOTALL,
    )
    
    def __init__(self, pipeline):
        """Initialize split phase.
        
        Args:
            pipeline: Pipeline instance
        """
        super().__init__(pipeline)
        self.metadata_by_file: Dict[str, DocumentMetadata] = {}
        self.attachments_by_main: Dict[str, Set[Path]] = {}
        self.section_stats = {
            'summary': {'processed': 0, 'empty': 0, 'error': 0},
            'raw_notes': {'processed': 0, 'empty': 0, 'error': 0},
            'attachments': {
                'processed': 0,
                'empty': 0,
                'error': 0
            }
        }

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0"
                )
            
            # Skip if not a markdown file or if it's in a subdirectory
            if not str(file_path).endswith('.parsed.md') or len(file_path.parts) > len(file_path.parent.parts) + 1:
                return None
            
            # Process the file
            return await self._process_file(file_path, output_dir, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to process file in split phase: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
                metadata.processed = False
                return metadata
            return None

    async def _process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0"
                )
            
            # Skip if not a markdown file or if it's in a subdirectory
            if not str(file_path).endswith('.parsed.md') or len(file_path.parts) > len(file_path.parent.parts) + 1:
                return None
            
            # Read content
            content = file_path.read_text()
            
            # Split content into sections
            sections = self._split_content(content)
            
            # Skip if no valid sections found
            if not sections or not any(key in sections for key in ['summary', 'raw_notes', 'attachments']):
                self.logger.warning(f"No valid sections found in {file_path}")
                if metadata:
                    metadata.add_error("SplitPhase", "No valid sections found")
                    metadata.processed = False
                    if file_path not in self.pipeline.state["split"]["failed_files"]:
                        self.pipeline.state["split"]["failed_files"].append(file_path)
                return None
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create output files if they don't exist
            summary_path = output_dir / "Summary.md"
            raw_notes_path = output_dir / "Raw Notes.md"
            attachments_path = output_dir / "Attachments.md"
            
            # Get file stem for linking
            file_stem = file_path.stem
            if file_stem.endswith('.parsed'):
                file_stem = file_stem[:-7]  # Remove .parsed suffix
                
            # Get date prefix from file name if available
            date_prefix = None
            if re.match(r'^\d{8}', file_stem):
                date_prefix = file_stem[:8]
            
            # Extract attachments and replace references in content
            attachments = self._extract_attachments(content, date_prefix)
            
            # Update summary file
            if 'summary' in sections:
                summary_content = sections['summary']
                
                # Replace attachment links with our new reference format
                for attach in attachments:
                    old_link = f'![{attach["text"] or ""}]({attach["url"]})'
                    summary_content = summary_content.replace(old_link, attach['reference'])
                    
                    # Also handle regular links
                    old_link = f'[{attach["text"]}]({attach["url"]})'
                    summary_content = summary_content.replace(old_link, attach['reference'])
                
                # Format the summary section
                summary_content = f"\n## {file_stem}\n\n{summary_content.strip()}\n"
                
                # Add link to raw notes at the end
                summary_content += f"\n---\nRaw Notes: [NOTE:{file_stem}]\n"
                
                # Check if content already exists
                existing_content = ""
                if summary_path.exists():
                    existing_content = summary_path.read_text()
                
                if summary_content not in existing_content:
                    if not summary_path.exists():
                        summary_path.write_text("# Summary\n")
                    with open(summary_path, 'a') as f:
                        f.write(summary_content)
                    metadata.add_output_file(summary_path)
                    self.section_stats['summary']['processed'] += 1
            else:
                self.section_stats['summary']['empty'] += 1
            
            # Update raw notes file
            if 'raw_notes' in sections:
                raw_notes = sections['raw_notes']
                
                # Replace attachment links with our new reference format
                for attach in attachments:
                    old_link = f'![{attach["text"] or ""}]({attach["url"]})'
                    raw_notes = raw_notes.replace(old_link, attach['reference'])
                    
                    # Also handle regular links
                    old_link = f'[{attach["text"]}]({attach["url"]})'
                    raw_notes = raw_notes.replace(old_link, attach['reference'])
                
                # Format the raw notes section
                raw_notes_content = f"\n## [NOTE:{file_stem}]\n\n{raw_notes.strip()}\n"
                
                # Check if content already exists
                existing_content = ""
                if raw_notes_path.exists():
                    existing_content = raw_notes_path.read_text()
                
                if raw_notes_content not in existing_content:
                    if not raw_notes_path.exists():
                        raw_notes_path.write_text("# Raw Notes\n")
                    with open(raw_notes_path, 'a') as f:
                        f.write(raw_notes_content)
                    metadata.add_output_file(raw_notes_path)
                    self.section_stats['raw_notes']['processed'] += 1
            else:
                self.section_stats['raw_notes']['empty'] += 1
            
            # Create attachments directory and copy files
            attachments_dir = output_dir / "attachments"
            attachments_dir.mkdir(exist_ok=True)
            
            # Copy attachments
            for attach in attachments:
                src_path = Path(attach["url"])
                if src_path.exists():
                    dst_path = attachments_dir / src_path.name
                    if not dst_path.exists():
                        shutil.copy2(src_path, dst_path)
                        metadata.add_output_file(dst_path)
                        self.section_stats['attachments']['processed'] += 1
                else:
                    self.logger.warning(f"Attachment {src_path} not found")
                    self.section_stats['attachments']['empty'] += 1
            
            # Create attachments section
            attachments_content = self._create_attachments_section(file_stem, attachments)
            attachments_path = output_dir / "Attachments.md"
            if not attachments_path.exists():
                attachments_path.write_text("# Attachments\n")
            with open(attachments_path, 'a') as f:
                f.write(attachments_content)
            metadata.add_output_file(attachments_path)
            
            # Store metadata for later use
            self.metadata_by_file[file_stem] = metadata
            
            # Mark as processed
            metadata.processed = True
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file in split phase: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
                metadata.processed = False
                return metadata
            return None

    def _update_links(
        self,
        content: str,
        source_file: str,
        metadata: DocumentMetadata
    ) -> str:
        """Update links in content.
        
        Args:
            content: Content to update
            source_file: Source file path
            metadata: Document metadata
            
        Returns:
            Updated content
        """
        def replace_link(match):
            """Replace a link match with updated link."""
            title = match.group(1)
            target = match.group(2)
            section = None
            
            # Check for section reference
            if '#' in target:
                target, section = target.split('#', 1)
            
            # Create link context
            link_context = LinkContext(
                source_file=source_file,
                target_file=target,
                target_section=section,
                link_type=LinkType.OUTGOING,
                title=title
            )
            
            # Add link to metadata
            metadata.add_link(link_context)
            
            return match.group(0)  # Return original link unchanged
        
        # Find and process all markdown links
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        content = re.sub(pattern, replace_link, content)
        
        return content

    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into sections.
        
        Args:
            content: Content to split
            
        Returns:
            Dictionary with 'summary', 'raw_notes', and 'attachments' sections
        """
        sections = {}
        
        # Find section markers
        summary_start = content.find('--==SUMMARY==--')
        raw_notes_start = content.find('--==RAW NOTES==--')
        attachments_start = content.find('--==ATTACHMENTS==--')
        
        # If no summary marker, treat content before first marker as summary
        if summary_start < 0:
            first_marker = min(
                (pos for pos in [raw_notes_start, attachments_start] if pos >= 0),
                default=len(content)
            )
            if first_marker > 0:
                # Get all content up to the first marker
                summary_content = content[:first_marker].strip()
                # Split into lines
                lines = summary_content.split('\n')
                # Skip the title line if it exists
                if lines and lines[0].startswith('# '):
                    lines = lines[1:]
                # Join the remaining lines
                sections['summary'] = '\n'.join(lines).strip()
        else:
            # Get summary content
            summary_content = content[summary_start + len('--==SUMMARY==--'):].strip()
            if raw_notes_start >= 0:
                summary_content = content[summary_start + len('--==SUMMARY==--'):raw_notes_start].strip()
            elif attachments_start >= 0:
                summary_content = content[summary_start + len('--==SUMMARY==--'):attachments_start].strip()
            sections['summary'] = summary_content
        
        if raw_notes_start >= 0:
            # Get raw notes content
            raw_notes_content = content[raw_notes_start + len('--==RAW NOTES==--'):].strip()
            if attachments_start >= 0:
                raw_notes_content = content[raw_notes_start + len('--==RAW NOTES==--'):attachments_start].strip()
            sections['raw_notes'] = raw_notes_content
            
        if attachments_start >= 0:
            # Get attachments content
            attachments_content = content[attachments_start + len('--==ATTACHMENTS==--'):].strip()
            sections['attachments'] = attachments_content
        
        return sections

    def _create_attachments_section(self, main_file: str, attachments: List[Dict[str, str]]) -> str:
        """Create attachments section markdown.
        
        Args:
            main_file: Main file name
            attachments: List of attachment dictionaries with text, url, reference, and type
            
        Returns:
            Markdown content for attachments section
        """
        if not attachments:
            return ""
            
        # Group attachments by type
        attachments_by_type = {}
        for attach in attachments:
            attach_type = attach['type']
            if attach_type not in attachments_by_type:
                attachments_by_type[attach_type] = []
            attachments_by_type[attach_type].append(attach)
            
        # Build markdown content
        content = []
        
        # Add each type section
        for attach_type in sorted(attachments_by_type.keys()):
            content.append(f"\n## {attach_type} Files")
            for attach in attachments_by_type[attach_type]:
                content.append(f"- [{attach['text']}]({attach['url']})")
                
        return "\n".join(content) + "\n"

    def _get_main_file_name(self, attachment_path: Path) -> str:
        """Get main file name from attachment path.
        
        Args:
            attachment_path: Path to attachment file
            
        Returns:
            Main file name
        """
        # Parent directory name is the main file name
        return attachment_path.parent.name

    def _update_section_stats(
        self,
        section: str,
        status: str,
        file_type: Optional[str] = None
    ) -> None:
        """Update section statistics.
        
        Args:
            section: Section name
            status: Status to update
            file_type: Optional file type for attachments
        """
        if section == 'attachments':
            if file_type not in self.section_stats[section][status]:
                self.section_stats[section][status][file_type] = 0
            self.section_stats[section][status][file_type] += 1
        else:
            self.section_stats[section][status] += 1

    def finalize(self) -> None:
        """Finalize the split phase.
        
        This method is called after all files have been processed.
        It performs any necessary cleanup and validation.
        """
        # Update pipeline state with section stats
        self.pipeline.state['split']['section_stats'] = self.section_stats
        
        # Log summary
        self.logger.info("Split phase completed")
        self.logger.info(f"Section stats: {self.section_stats}")
        
        # Check for any failed files
        failed_files = self.pipeline.state['split']['failed_files']
        if failed_files:
            self.logger.warning(f"Failed to process {len(failed_files)} files:")
            for file_path in failed_files:
                self.logger.warning(f"  - {file_path}")
        
        # Check for empty sections
        for section, stats in self.section_stats.items():
            if section != 'attachments' and stats['empty'] > 0:
                self.logger.warning(f"Found {stats['empty']} empty {section} sections")
            elif section == 'attachments' and stats['empty'] > 0:
                self.logger.warning(f"Found {stats['empty']} missing attachments")

    def _extract_attachments(self, content: str, date_prefix: str = None) -> List[Dict]:
        """Find all embedded attachments in the main file's markdown links.
        
        Args:
            content: Content to extract attachments from
            date_prefix: Optional date prefix for attachment IDs
            
        Returns:
            List of dictionaries with attachment info
        """
        attachments = []
        for match in self.attachment_pattern.finditer(content):
            text = match.group("text")
            url = match.group("url")
            
            if url.endswith('.parsed.md'):
                # Get the attachment type from the original file
                original_path = url[:-10]  # Remove .parsed.md
                attach_type = self._get_attachment_type(original_path)
                
                # Generate unique ID
                attach_id = self._generate_attachment_id(url, date_prefix)
                
                attachments.append({
                    "url": url,
                    "text": text,
                    "type": attach_type,
                    "id": attach_id,
                    "reference": self._format_attachment_reference(attach_type, attach_id)
                })
        
        return attachments

    def _build_attachments_markdown(self, main_file: str, attachments: List[Dict], file_path: Path) -> str:
        """Build the markdown content for the attachments section.
        
        Args:
            main_file: Main file name
            attachments: List of attachment dictionaries
            file_path: Path to the main file
            
        Returns:
            Markdown content for attachments section
        """
        if not attachments:
            return ""
            
        result = []
        
        # Group attachments by type
        attachments_by_type = {}
        for attach in attachments:
            attach_type = attach['type']
            if attach_type not in attachments_by_type:
                attachments_by_type[attach_type] = []
            attachments_by_type[attach_type].append(attach)
        
        # Process each type in order
        for attach_type in sorted(attachments_by_type.keys()):
            type_attachments = attachments_by_type[attach_type]
            
            for attach in type_attachments:
                # Add the attachment reference as a header
                result.append(f"\n## {attach['reference']}\n")
                
                # Get the attachment path
                url = unquote(attach['url'])
                attachment_path = None
                
                if '/' in url:
                    # If path has directory, look in that directory
                    dir_name = url.split('/')[0]
                    dir_path = file_path.parent / dir_name
                    
                    # Get the base name without extensions
                    base_name = Path(url).name
                    if base_name.endswith('.parsed.md'):
                        base_name = base_name[:-10]  # Remove .parsed.md
                    if '.' in base_name:
                        base_name = base_name[:base_name.rindex('.')]  # Remove file extension
                    
                    # Try to find a matching file
                    for candidate in dir_path.glob('*.parsed.md'):
                        candidate_base = candidate.stem
                        if candidate_base.endswith('.parsed'):
                            candidate_base = candidate_base[:-7]  # Remove .parsed suffix
                        
                        # Compare base names (ignoring extensions)
                        if candidate_base == base_name:
                            attachment_path = candidate
                            break
                else:
                    attachment_path = file_path.parent / url
                
                # Read and include the actual content of the attachment
                if attachment_path and attachment_path.exists():
                    try:
                        content = attachment_path.read_text()
                        if content.strip():
                            # Add metadata if available
                            if attach.get('text'):
                                result.append(f"\n### Title\n{attach['text']}\n")
                            
                            # Add the actual content
                            result.append("\n### Content\n")
                            result.append(content.strip())
                    except Exception as e:
                        self.logger.warning(f"Failed to read attachment content from {attachment_path}: {e}")
                else:
                    self.logger.warning(f"Attachment not found: {url}")
                
                result.append("\n")
        
        return "\n".join(result) if result else ""

    def _get_attachment_type(self, file_path: str) -> str:
        """Get the attachment type identifier from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.TYPE_MAP.get(ext, 'DOC')
        
    def _generate_attachment_id(self, file_path: str, date_prefix: str = None) -> str:
        """Generate a unique attachment identifier."""
        # Get base name without extensions
        base = Path(file_path).stem
        if base.endswith('.parsed'):
            base = base[:-7]
        
        # Remove any file extension
        if '.' in base:
            base = base[:base.rindex('.')]
            
        # Clean the base name
        clean_base = re.sub(r'[^a-zA-Z0-9]+', '-', base).lower().strip('-')
        
        # Add date prefix if provided
        if date_prefix:
            return f"{date_prefix}-{clean_base}"
        return clean_base
        
    def _format_attachment_reference(self, attach_type: str, attach_id: str) -> str:
        """Format an attachment reference."""
        return f"[ATTACH:{attach_type}:{attach_id}]"