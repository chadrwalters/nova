"""Split phase of the Nova pipeline."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, NamedTuple
import os
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote
from datetime import datetime
import traceback

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from .base import Phase
from nova.core.metadata import FileMetadata


logger = logging.getLogger(__name__)


class ParsedFileMetadata(NamedTuple):
    """Metadata about a parsed markdown file."""
    raw_notes_pos: int  # Position of RAW NOTES marker, or -1 if not found
    attachments: List[str]  # List of attachment references found


class SplitPhase(Phase):
    """Phase that splits parsed files into smaller chunks."""
    
    def __init__(self, pipeline):
        """Initialize the split phase.
        
        Args:
            pipeline: Pipeline instance
        """
        super().__init__(pipeline)
        self.attachments_by_main = {}  # Map of main file name to set of attachment paths
        self.metadata_by_file = {}  # Map of file name to metadata
        self.output_files = set()  # Set of output files created
        
        # Initialize state with detailed section tracking
        self.pipeline.state['split'] = {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'section_stats': {
                'summary': {
                    'total': 0,
                    'processed': 0,
                    'empty': 0,
                    'errors': 0
                },
                'raw_notes': {
                    'total': 0,
                    'processed': 0,
                    'empty': 0,
                    'errors': 0
                },
                'attachments': {
                    'total': 0,
                    'processed': 0,
                    'by_type': {},  # Track attachment types
                    'errors': 0
                }
            }
        }
    
    def _ensure_section_stats(self):
        """Ensure section stats are properly initialized in the pipeline state."""
        if 'split' not in self.pipeline.state:
            self.pipeline.state['split'] = {}
            
        state = self.pipeline.state['split']
        
        # Initialize basic state tracking if not present
        if 'successful_files' not in state:
            state['successful_files'] = set()
        if 'failed_files' not in state:
            state['failed_files'] = set()
        if 'skipped_files' not in state:
            state['skipped_files'] = set()
            
        # Initialize section stats if not present
        if 'section_stats' not in state:
            state['section_stats'] = {
                'summary': {
                    'total': 0,
                    'processed': 0,
                    'empty': 0,
                    'errors': 0
                },
                'raw_notes': {
                    'total': 0,
                    'processed': 0,
                    'empty': 0,
                    'errors': 0
                },
                'attachments': {
                    'total': 0,
                    'processed': 0,
                    'by_type': {},
                    'errors': 0
                }
            }
            
    def _update_section_stats(self, section_type: str, status: str, attachment_type: Optional[str] = None):
        """Update section statistics.
        
        Args:
            section_type: Type of section ('summary', 'raw_notes', 'attachments')
            status: Status of processing ('processed', 'empty', 'error')
            attachment_type: Type of attachment if section_type is 'attachments'
        """
        # Ensure stats are initialized
        self._ensure_section_stats()
        
        stats = self.pipeline.state['split']['section_stats'][section_type]
        stats['total'] += 1
        
        if status == 'processed':
            stats['processed'] += 1
            if section_type == 'attachments' and attachment_type:
                if attachment_type not in stats['by_type']:
                    stats['by_type'][attachment_type] = 0
                stats['by_type'][attachment_type] += 1
        elif status == 'empty':
            stats['empty'] += 1
        elif status == 'error':
            stats['errors'] += 1
    
    async def process(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
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
                metadata = FileMetadata(file_path)
            
            # Process the file
            metadata = await self.process_file(file_path, output_dir, metadata)
            if metadata:
                # Get the file stem (without extension)
                file_stem = file_path.stem
                if file_stem.endswith('.parsed'):
                    file_stem = file_stem[:-7]  # Remove .parsed suffix
                
                # Store metadata for later use
                self.metadata_by_file[file_stem] = metadata
                
                return metadata
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to process file in split phase: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
                metadata.processed = False
                return metadata
            return None
        
    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file through the split phase.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Document metadata if successful, None otherwise
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata(file_path)
            
            # Get the file stem (without extension)
            file_stem = file_path.stem
            if file_stem.endswith('.parsed'):
                file_stem = file_stem[:-7]  # Remove .parsed suffix
            
            # Get the parent directory name
            parent_dir = file_path.parent.name
            
            # If this is a main file (not in a subdirectory)
            if parent_dir == 'parse':
                # Read content from file
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Split content into sections
                    summary, raw_notes = self._split_content(content)
                    
                    # Update summary stats
                    if summary:
                        self._update_section_stats('summary', 'processed')
                    else:
                        self._update_section_stats('summary', 'empty')
                    
                    # Update raw notes stats
                    if raw_notes:
                        self._update_section_stats('raw_notes', 'processed')
                    else:
                        self._update_section_stats('raw_notes', 'empty')
                    
                    # Process attachments
                    attachments = self._extract_attachments(content)
                    for attachment in attachments:
                        attachment_type = attachment.suffix.lower().lstrip('.')
                        self._update_section_stats('attachments', 'processed', attachment_type)
                    
                    # Create output files
                    summary_file = output_dir / "Summary.md"
                    raw_notes_file = output_dir / "Raw Notes.md"
                    
                    # Write summary
                    if not summary_file.exists():
                        summary_file.write_text("# Summary\n\n", encoding='utf-8')
                    with open(summary_file, 'a', encoding='utf-8') as f:
                        if summary:
                            f.write(f"\n## {file_stem}\n\n{summary}\n")
                    
                    # Write raw notes
                    if not raw_notes_file.exists():
                        raw_notes_file.write_text("# Raw Notes\n\n", encoding='utf-8')
                    with open(raw_notes_file, 'a', encoding='utf-8') as f:
                        if raw_notes:
                            f.write(f"\n## {file_stem}\n\n{raw_notes}\n")
                    
                    # Add output files to metadata
                    metadata.add_output_file(summary_file)
                    metadata.add_output_file(raw_notes_file)
                    
                    # Add to output files set
                    self.output_files.add(summary_file)
                    self.output_files.add(raw_notes_file)
                    
                    # Mark file as successful
                    self.pipeline.state['split']['successful_files'].add(file_path)
                    metadata.processed = True
                    
                    return metadata
                    
                except Exception as e:
                    self.logger.error(f"Failed to process main file {file_path}: {e}")
                    self.logger.error(traceback.format_exc())
                    self._update_section_stats('summary', 'error')
                    self._update_section_stats('raw_notes', 'error')
                    self.pipeline.state['split']['failed_files'].add(file_path)
                    metadata.add_error("SplitPhase", str(e))
                    metadata.processed = False
                    return metadata
                
            else:
                # This is an attachment file
                # Add this attachment to the main file's list
                main_file_name = self._get_main_file_name(file_path)
                if main_file_name not in self.attachments_by_main:
                    self.attachments_by_main[main_file_name] = set()
                self.attachments_by_main[main_file_name].add(file_path)
                
                # Update attachment stats
                attachment_type = file_path.suffix.lower().lstrip('.')
                self._update_section_stats('attachments', 'processed', attachment_type)
                
                # Mark file as successful
                self.pipeline.state['split']['successful_files'].add(file_path)
                metadata.processed = True
                
                return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
                metadata.processed = False
                return metadata
            return None
            
    def finalize(self):
        """Process all attachments in a single pass."""
        # Process all attachments in a single pass
        output_dir = self.pipeline.config.processing_dir / "phases" / "split"
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        attachments_file = output_dir / "Attachments.md"
        
        # Create Attachments.md with initial header
        with open(attachments_file, 'w', encoding='utf-8') as f:
            # Write initial header
            f.write("# Attachments\n\n")
            logger.info(f"Created {attachments_file} and wrote initial header")
            
            # Only process attachments if we have any
            if self.attachments_by_main:
                logger.info(f"Processing {len(self.attachments_by_main)} main files with attachments")
                
                # Process each main file's attachments
                for main_file_name, attachments in sorted(self.attachments_by_main.items()):
                    logger.info(f"Processing {len(attachments)} attachments for {main_file_name}")
                    
                    # Add main file header
                    f.write(f"\n## {main_file_name}\n\n")
                    logger.info(f"Wrote header for {main_file_name}")
                    
                    # Process each attachment
                    for attachment_path in sorted(attachments):
                        try:
                            logger.info(f"Processing attachment {attachment_path}")
                            if self._process_attachment(attachment_path, main_file_name, f):
                                # Update attachment count
                                self.pipeline.state['split']['attachments'] += 1
                                # Add to metadata
                                if main_file_name in self.metadata_by_file:
                                    self.metadata_by_file[main_file_name].add_output_file(attachments_file)
                                logger.info(f"Successfully processed attachment {attachment_path}")
                            else:
                                # Mark attachment as failed
                                logger.error(f"Failed to process attachment {attachment_path}")
                                self.pipeline.state['split']['failed_files'].add(attachment_path)
                        except Exception as e:
                            logger.error(f"Error processing attachment {attachment_path}: {e}")
                            logger.error(traceback.format_exc())
                            self.pipeline.state['split']['failed_files'].add(attachment_path)
            else:
                logger.info("No attachments to process")
            
            # Ensure all content is written
            f.flush()
            logger.info(f"Flushed content to {attachments_file}")
        
        # Add Attachments.md to output files
        self.output_files.add(attachments_file)
        logger.info(f"Successfully created {attachments_file}")
        
    def _normalize_main_file_name(self, file_name: str) -> str:
        """Normalize a main file name by removing the .parsed suffix if present.
        
        Args:
            file_name: The file name to normalize
            
        Returns:
            The normalized file name
        """
        if file_name.endswith('.parsed'):
            return file_name[:-7]  # Remove .parsed suffix
        return file_name
        
    def _get_main_file_name(self, file_path: Path) -> str:
        """Get the normalized main file name from a file path.
        
        This handles both main files (using their stem) and attachments
        (using their parent directory name).
        
        Args:
            file_path: The file path to get the main file name from
            
        Returns:
            The normalized main file name
        """
        # Get the input directory and parse directory
        input_dir = Path(self.pipeline.config.input_dir)
        parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
        
        try:
            # Try to get relative path from input directory
            rel_path = file_path.relative_to(input_dir)
            # Get the first directory name as the main file name
            main_file_name = rel_path.parts[0]
            # Remove date prefix if present (e.g., "20241226 - ")
            if main_file_name.startswith("2024"):
                main_file_name = " - ".join(main_file_name.split(" - ")[1:])
            return main_file_name
        except ValueError:
            try:
                # Try to get relative path from parse directory
                rel_path = file_path.relative_to(parse_dir)
                # If this is an attachment (in a subdirectory), use the directory name
                if len(rel_path.parts) > 1:
                    main_file_name = self._normalize_main_file_name(rel_path.parts[0])
                    return main_file_name
                
                # Otherwise, use the file stem
                main_file_name = self._normalize_main_file_name(file_path.stem)
                return main_file_name
            except ValueError:
                # If both attempts fail, just use the file stem
                main_file_name = self._normalize_main_file_name(file_path.stem)
                return main_file_name
        
    def _split_content(self, content: str) -> Tuple[str, str]:
        """Split content into summary and raw notes.
        
        Args:
            content: Content to split.
            
        Returns:
            Tuple of (summary, raw_notes).
        """
        # Find raw notes marker
        raw_notes_marker = "--==RAW NOTES==--"
        raw_notes_pos = content.find(raw_notes_marker)
        
        # Split content
        if raw_notes_pos >= 0:
            summary = content[:raw_notes_pos].strip()
            raw_notes = content[raw_notes_pos + len(raw_notes_marker):].strip()
        else:
            summary = content.strip()
            raw_notes = ""
        
        return summary, raw_notes
        
    def _update_links(self, content: str, section_id: str) -> str:
        """Update links in content to point to the correct sections.
        
        Args:
            content: Content to update links in.
            section_id: ID of the current section.
            
        Returns:
            Updated content with corrected links.
        """
        def replace_link(match):
            full_match = match.group(0)
            link_text = match.group(2)
            path = match.group(3)
            
            # URL decode the path
            path = unquote(path)
            
            # If it's a .parsed.md file, link to the attachments section
            if path.endswith('.parsed.md'):
                # Get the filename without .parsed.md
                filename = Path(path).stem
                if filename.endswith('.parsed'):
                    filename = filename[:-7]  # Remove .parsed suffix
                
                # Create the link to the attachments section
                section_link = f"Attachments.md#{section_id}-{filename}"
                
                # Remove any double brackets from link text
                if link_text.startswith('[') and link_text.endswith(']'):
                    link_text = link_text[1:-1]  # Remove outer brackets
                
                # Preserve image or standard link format
                if full_match.startswith('!'):
                    return f"![{link_text}]({section_link})"
                else:
                    return f"[{link_text}]({section_link})"
            
            return full_match
        
        pattern = r'(!?\[(.*?)\])\((.*?)\)(?:<!-- \{.*?\} -->)?'
        content = re.sub(pattern, replace_link, content)
        
        # Fix any remaining double brackets
        content = re.sub(r'\[\[(.*?)\]\]', r'[\1]', content)
        
        return content
        
    def _process_attachment(self, attachment_path: Path, main_file_name: str, output_file) -> bool:
        """Process a single attachment and write it to the output file.
        
        Args:
            attachment_path: Path to the attachment file
            main_file_name: Name of the main file this attachment belongs to
            output_file: File object to write the processed attachment to
            
        Returns:
            True if attachment was processed successfully, False otherwise
        """
        try:
            # Check if attachment file exists
            if not attachment_path.exists():
                logger.error(f"Attachment file does not exist: {attachment_path}")
                return False
                
            # Check if attachment file is empty
            if attachment_path.stat().st_size == 0:
                logger.error(f"Attachment file is empty: {attachment_path}")
                return False
                
            # Get original filename without .parsed.md
            filename = attachment_path.stem
            if filename.endswith('.parsed'):
                filename = filename[:-7]  # Remove .parsed suffix
            
            # Get original extension from filename before .parsed.md
            original_ext = Path(filename).suffix
            if original_ext:
                filename = Path(filename).stem  # Remove the original extension
            
            # Read the attachment content
            try:
                attachment_content = attachment_path.read_text(encoding='utf-8')
                if not attachment_content.strip():
                    logger.error(f"Attachment content is empty after stripping whitespace: {attachment_path}")
                    return False
            except Exception as e:
                logger.error(f"Failed to read attachment content from {attachment_path}: {e}")
                logger.error(traceback.format_exc())
                return False
            
            # Create section ID by replacing spaces with hyphens
            section_id = f"{main_file_name}-{filename}"
            section_id = re.sub(r'[^a-zA-Z0-9-]', '-', section_id)
            section_id = re.sub(r'-+', '-', section_id)
            section_id = section_id.strip('-').lower()
            
            # Update links in the attachment content
            try:
                attachment_content = self._update_links(attachment_content, section_id)
            except Exception as e:
                logger.error(f"Failed to update links in attachment content for {filename}: {e}")
                logger.error(traceback.format_exc())
                return False
            
            # Write the attachment content with proper header
            try:
                # Add original extension to header if it exists
                header_text = filename
                if original_ext:
                    header_text = f"{filename}{original_ext}"
                
                # Write header and anchor
                output_file.write(f"\n### {header_text}\n")
                output_file.write(f'<a id="{section_id}"></a>\n\n')
                
                # Skip the title line if it starts with # filename
                content_lines = attachment_content.splitlines()
                if content_lines and content_lines[0].strip() == f"# {filename}":
                    content_lines = content_lines[1:]
                
                # Write content and separator
                output_file.write("\n".join(content_lines).strip() + "\n\n")
                output_file.write("---\n\n")
                
                # Ensure content is written
                output_file.flush()
                
                # Track successful attachment
                self.successful_attachments.add(attachment_path)
                
                # Mark attachment as successful
                self.pipeline.state['split']['successful_files'].add(attachment_path)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to write attachment content for {filename}: {e}")
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            logger.error(f"Error processing attachment {attachment_path}: {e}")
            logger.error(traceback.format_exc())
            self.pipeline.state['split']['failed_files'].add(attachment_path)
            return False

    def print_summary(self):
        """Print a summary of the split phase results."""
        state = self.pipeline.state['split']
        section_stats = state['section_stats']
        
        # Print overall stats
        print("\nSplit Phase Summary:")
        print("===================")
        print(f"Total files processed: {len(state['successful_files']) + len(state['failed_files'])}")
        print(f"Successful files: {len(state['successful_files'])}")
        print(f"Failed files: {len(state['failed_files'])}")
        print(f"Skipped files: {len(state['skipped_files'])}")
        
        # Print section stats
        print("\nSection Statistics:")
        print("-----------------")
        
        # Summary section stats
        summary_stats = section_stats['summary']
        print("\nSummary Sections:")
        print(f"  Total: {summary_stats['total']}")
        print(f"  Processed: {summary_stats['processed']}")
        print(f"  Empty: {summary_stats['empty']}")
        print(f"  Errors: {summary_stats['errors']}")
        
        # Raw notes section stats
        raw_notes_stats = section_stats['raw_notes']
        print("\nRaw Notes Sections:")
        print(f"  Total: {raw_notes_stats['total']}")
        print(f"  Processed: {raw_notes_stats['processed']}")
        print(f"  Empty: {raw_notes_stats['empty']}")
        print(f"  Errors: {raw_notes_stats['errors']}")
        
        # Attachments stats
        attachment_stats = section_stats['attachments']
        print("\nAttachments:")
        print(f"  Total: {attachment_stats['total']}")
        print(f"  Processed: {attachment_stats['processed']}")
        print(f"  Errors: {attachment_stats['errors']}")
        
        # Print attachment types if any were processed
        if attachment_stats['by_type']:
            print("\nAttachment Types:")
            for file_type, count in sorted(attachment_stats['by_type'].items()):
                print(f"  {file_type}: {count}")
        
        # Print any failed files
        if state['failed_files']:
            print("\nFailed Files:")
            for file in sorted(state['failed_files']):
                print(f"  {file}")

    def _extract_attachments(self, content: str) -> List[Path]:
        """Extract attachment paths from content.
        
        Args:
            content: Content to extract attachments from
            
        Returns:
            List of attachment paths
        """
        attachments = []
        
        # Find all markdown links
        pattern = r'!\[(.*?)\]\((.*?)\)'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            path_str = match.group(2)
            # URL decode the path
            path_str = unquote(path_str)
            # Convert to Path object
            path = Path(path_str)
            attachments.append(path)
            
        return attachments