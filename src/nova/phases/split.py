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
        '.md': 'DOC',
        '.parsed.md': 'DOC'
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
            'attachments': {'processed': 0, 'empty': 0, 'error': 0}
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
            
            # Read the file content
            self.logger.debug(f"Reading content from {file_path}")
            content = file_path.read_text()
            
            # Get date prefix from file name
            date_prefix = None
            if re.match(r'\d{8}', file_path.stem):
                date_prefix = file_path.stem[:8]
            
            # Extract attachments before splitting content
            self.logger.debug("Extracting attachments")
            attachments = self._extract_attachments(content, date_prefix)
            self.logger.debug(f"Found {len(attachments)} attachments")
            
            # Split content into sections
            self.logger.debug("Splitting content into sections")
            sections = self._split_content(content)
            self.logger.debug(f"Found sections: {list(sections.keys())}")
            
            # Process summary section
            summary_content = sections.get('summary', '')
            if summary_content:
                self.logger.debug("Processing summary section")
                # Get the title from the first line if it exists
                title = file_path.stem
                if title.endswith('.parsed'):
                    title = title[:-7]
                
                # Add title to summary
                summary_content = f"## {title}\n\n{summary_content}"
                
                # Update links in summary
                summary_content = self._update_links(summary_content, str(file_path), metadata)
                
                # Add to summary file
                summary_path = output_dir / 'Summary.md'
                if not summary_path.exists():
                    summary_path.write_text("# Summary\n\n")
                with open(summary_path, 'a') as f:
                    f.write(f"\n{summary_content}\n")
                    f.write(f"\n---\nRaw Notes: [NOTE:{title}]\n")
                
                self._update_section_stats('summary', 'processed')
                metadata.add_output_file(summary_path)
            else:
                self._update_section_stats('summary', 'empty')
            
            # Process raw notes section
            raw_notes_content = sections.get('raw_notes', '')
            if raw_notes_content:
                self.logger.debug("Processing raw notes section")
                # Get the title
                title = file_path.stem
                if title.endswith('.parsed'):
                    title = title[:-7]
                
                # Add title to raw notes
                raw_notes_content = f"## [NOTE:{title}]\n\n{raw_notes_content}"
                
                # Update links in raw notes
                raw_notes_content = self._update_links(raw_notes_content, str(file_path), metadata)
                
                # Add to raw notes file
                raw_notes_path = output_dir / 'Raw Notes.md'
                if not raw_notes_path.exists():
                    raw_notes_path.write_text("# Raw Notes\n\n")
                with open(raw_notes_path, 'a') as f:
                    f.write(f"\n{raw_notes_content}\n")
                
                self._update_section_stats('raw_notes', 'processed')
                metadata.add_output_file(raw_notes_path)
            else:
                self._update_section_stats('raw_notes', 'empty')
            
            # Process attachments
            if attachments:
                self.logger.debug("Processing attachments")
                # Create attachments directory
                attachments_dir = output_dir / 'attachments'
                attachments_dir.mkdir(exist_ok=True)
                
                # Add to attachments file
                attachments_path = output_dir / 'Attachments.md'
                
                # Initialize or read existing content
                if not attachments_path.exists():
                    existing_content = "# Attachments\n\n"
                else:
                    existing_content = attachments_path.read_text()
                
                # Group attachments by type
                attachments_by_type = {}
                for attach in attachments:
                    attach_type = attach['type']
                    if attach_type not in attachments_by_type:
                        attachments_by_type[attach_type] = []
                    attachments_by_type[attach_type].append(attach)
                
                # Update content for each section
                for attach_type in sorted(attachments_by_type.keys()):
                    section_header = f"\n## {attach_type} Files\n"
                    section_start = existing_content.find(section_header)
                    
                    if section_start < 0:
                        # Section doesn't exist, add it
                        existing_content += section_header
                        
                        # Add attachments to section
                        for attach in attachments_by_type[attach_type]:
                            if attach['is_image']:
                                existing_content += f"- {attach['original']}\n"
                            else:
                                link = f"- [{attach['text']}]({attach['url']})"
                                if attach['metadata']:
                                    link += f" <!-- {attach['metadata']} -->"
                                existing_content += f"{link}\n"
                        existing_content += "\n"  # Add blank line after section
                
                # Write the complete content back to file
                attachments_path.write_text(existing_content)
                
                self._update_section_stats('attachments', 'processed')
                metadata.add_output_file(attachments_path)
            else:
                self._update_section_stats('attachments', 'empty')
            
            # Mark as processed
            metadata.processed = True
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file in split phase: {file_path}")
            self.logger.error(f"Error details: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            if metadata:
                metadata.add_error("SplitPhase", str(e))
                metadata.processed = False
            return None

    def _update_links(
        self,
        content: str,
        source_file: str,
        metadata: DocumentMetadata
    ) -> str:
        """Update links in content, ensuring we don't double-append .parsed.md."""
        def replace_link(match):
            text = match.group("text") or ""
            url = match.group("url") or ""
            link_metadata = match.group("metadata")
            is_image = match.group(0).startswith('!')

            if not url:
                return match.group(0)

            decoded_url = unquote(url)
            path_obj = Path(decoded_url)

            # Remove .parsed.md if it exists
            if str(path_obj).endswith(".parsed.md"):
                path_obj = path_obj.parent / path_obj.stem[:-7]

            # Build the new link
            if is_image:
                # Image syntax
                return f"![{text}]({path_obj})"
            else:
                # Regular link syntax
                link = f"[{text}]({path_obj})"
                if link_metadata:
                    link += f" <!-- {link_metadata} -->"
                return link

        # Update all links in the content
        return self.attachment_pattern.sub(replace_link, content)

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
        
        # If no markers found, treat the whole content as summary
        if summary_start < 0 and raw_notes_start < 0 and attachments_start < 0:
            # Get all content
            lines = content.split('\n')
            # Skip the title line if it exists
            if lines and lines[0].startswith('# '):
                lines = lines[1:]
            # Join the remaining lines
            sections['summary'] = '\n'.join(lines).strip()
            return sections
        
        # Get summary content
        if summary_start >= 0:
            # Get content from after summary marker to next marker or end
            next_marker = min(
                (pos for pos in [raw_notes_start, attachments_start] if pos >= 0),
                default=len(content)
            )
            sections['summary'] = content[summary_start + len('--==SUMMARY==--'):next_marker].strip()
        else:
            # If no summary marker, get content from start to first marker
            first_marker = min(
                (pos for pos in [raw_notes_start, attachments_start] if pos >= 0),
                default=len(content)
            )
            # Get all content up to the first marker
            summary_content = content[:first_marker].strip()
            # Split into lines
            lines = summary_content.split('\n')
            # Skip the title line if it exists
            if lines and lines[0].startswith('# '):
                lines = lines[1:]
            # Join the remaining lines
            sections['summary'] = '\n'.join(lines).strip()
        
        # Get raw notes content
        if raw_notes_start >= 0:
            # Get content from after raw notes marker to next marker or end
            next_marker = min(
                (pos for pos in [attachments_start] if pos >= 0 and pos > raw_notes_start),
                default=len(content)
            )
            sections['raw_notes'] = content[raw_notes_start + len('--==RAW NOTES==--'):next_marker].strip()
        
        # Get attachments content
        if attachments_start >= 0:
            sections['attachments'] = content[attachments_start + len('--==ATTACHMENTS==--'):].strip()
        
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
            file_type: Optional file type
        """
        if section in self.section_stats and status in self.section_stats[section]:
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
        """
        Find all embedded attachments in the main file's markdown links, ensuring
        we don't double-append .parsed.md in attachment paths.
        """
        attachments = []
        processed_bases = {}

        # Get output directory for attachments
        output_dir = self.pipeline.get_phase_output_dir("split")
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        for match in self.attachment_pattern.finditer(content):
            text = match.group("text")
            url = match.group("url")
            meta_comment = match.group("metadata")

            if not url:
                continue

            decoded_url = unquote(url)
            path_obj = Path(decoded_url)

            # Remove .parsed.md if it exists
            if str(path_obj).endswith(".parsed.md"):
                path_obj = path_obj.parent / path_obj.stem[:-7]

            # Identify initial attachment type
            attach_type = self._get_attachment_type(decoded_url)

            # Build the effective path in the input directory:
            input_dir = Path(self.pipeline.config.input_dir)
            
            # Try both with and without parent directory
            input_path = input_dir / path_obj
            if not input_path.exists():
                # Try without parent directory
                input_path = input_dir / path_obj.parent.name / path_obj.name
                if not input_path.exists():
                    # Try just the name in the parent directory
                    input_path = input_dir / path_obj.parent.name / path_obj.stem / path_obj.name
                    if not input_path.exists():
                        self.logger.warning(f"Attachment {decoded_url} not found")
                        continue

            # Make sure we haven't processed the same "stem" repeatedly
            # (avoid duplicates by base name)
            base_stem = path_obj.stem  # Use original stem without .parsed
            if base_stem in processed_bases:
                self.logger.debug(f"Skipping duplicate reference for base name {base_stem}")
                continue
            processed_bases[base_stem] = attach_type

            # Copy the attachment to the split phase's attachments directory, preserving directory structure
            dest_path = attachments_dir / path_obj.parent.name / path_obj.name
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(input_path, dest_path)
                self.logger.debug(f"Copied attachment {input_path} to {dest_path}")
            except Exception as e:
                self.logger.error(f"Failed to copy attachment {input_path} to {dest_path}: {str(e)}")
                continue

            attach_id = self._generate_attachment_id(url, date_prefix)
            attachments.append({
                "url": str(dest_path.relative_to(output_dir)),  # Update URL to point to new location
                "text": text or path_obj.name,
                "type": attach_type,
                "id": attach_id,
                "metadata": meta_comment,
                "is_image": match.group(0).startswith('!'),
                "original": match.group(0),
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
            
            # Add type header once
            result.append(f"\n## {attach_type} Files")
            
            for attach in type_attachments:
                # Use the original markdown format for the link
                if attach['is_image']:
                    result.append(f"- {attach['original']}")
                else:
                    link = f"- [{attach['text']}]({attach['url']})"
                    if attach['metadata']:
                        link += f" <!-- {attach['metadata']} -->"
                    result.append(link)
            
            result.append("")  # Add blank line between sections
        
        return "\n".join(result)

    def _get_attachment_type(self, url: str) -> str:
        """Get attachment type from URL.
        
        Args:
            url: URL to get type from
            
        Returns:
            Attachment type
        """
        # Get the file extension
        path_obj = Path(url)
        stem = path_obj.stem
        if stem.endswith('.parsed'):
            stem = stem[:-7]
        
        # Get the extension from the stem
        for ext in self.TYPE_MAP.keys():
            if stem.lower().endswith(ext[1:]):  # Remove the leading dot from the extension
                return self.TYPE_MAP[ext]
        
        # If no extension found in stem, try the original extension
        ext = path_obj.suffix.lower()
        if ext in self.TYPE_MAP:
            return self.TYPE_MAP[ext]
            
        # Default to DOC type
        return 'DOC'
        
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