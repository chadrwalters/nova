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
        self.successful_attachments = set()  # Set of successfully processed attachments
        self.output_files = set()  # Set of output files
        self.processed_files = set()  # Set of processed files
        
        # Initialize state
        self.pipeline.state['split'] = {
            'attachments': 0,  # Number of attachments processed
            'successful_files': set(),  # Set of successfully processed files
            'failed_files': set(),  # Set of failed files
            'skipped_files': set(),  # Set of skipped files
            'summary_sections': 0,  # Number of summary sections processed
            'raw_notes_sections': 0  # Number of raw notes sections processed
        }
        
    async def process(self, file_path: Path, output_dir: Path, metadata: Optional[FileMetadata] = None) -> Optional[FileMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        # Call the sync version of process_file
        metadata = await self.process_file(file_path, output_dir)
        if metadata:
            # Get the file stem (without extension)
            file_stem = file_path.stem
            if file_stem.endswith('.parsed'):
                file_stem = file_stem[:-7]  # Remove .parsed suffix
            
            # Store metadata for later use
            self.metadata_by_file[file_stem] = metadata
            
            return metadata
        return None
        
    async def process_file(self, file_path: Path, output_dir: Optional[Path] = None) -> Optional[FileMetadata]:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            output_dir: Optional directory to write output files to
            
        Returns:
            FileMetadata if file was processed successfully, None otherwise
        """
        try:
            # Get the file stem (without extension)
            file_stem = file_path.stem
            if file_stem.endswith('.parsed'):
                file_stem = file_stem[:-7]  # Remove .parsed suffix
            
            # Get the parent directory name
            parent_dir = file_path.parent.name
            
            # Create metadata for the file
            metadata = FileMetadata(file_path)
            metadata.processed = True
            metadata.unchanged = False  # File was processed, so it's not unchanged
            metadata.reprocessed = False  # Not reprocessing in this phase
            
            # If this is a main file (not in a subdirectory)
            if parent_dir == 'parse':
                logger.info(f"Processing main file: {file_path}")
                # Use file stem for main file
                main_file_name = file_stem
                logger.debug(f"Using file stem for main file: {main_file_name} (from {file_path})")
                # Store metadata for main file
                self.metadata_by_file[main_file_name] = metadata
                logger.debug(f"Storing metadata for main file: {main_file_name}")
                
                # Read the file content
                try:
                    content = file_path.read_text(encoding='utf-8')
                    logger.info(f"Successfully read content from {file_path}: {len(content)} characters")
                    
                    # Split content into summary and raw notes
                    summary, raw_notes = self._split_content(content)
                    
                    # Create output directory if it doesn't exist
                    output_dir = self.pipeline.config.processing_dir / "phases" / "split"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write summary to Summary.md
                    if summary:
                        summary_file = output_dir / "Summary.md"
                        try:
                            # Create file if it doesn't exist
                            if not summary_file.exists():
                                with open(summary_file, 'w', encoding='utf-8') as f:
                                    f.write("# Summary\n\n")
                            
                            # Append summary section
                            with open(summary_file, 'a', encoding='utf-8') as f:
                                f.write(f"\n## {main_file_name}\n\n")
                                f.write(summary + "\n\n")
                                f.write("---\n\n")
                            
                            # Add to metadata
                            metadata.add_output_file(summary_file)
                            self.output_files.add(summary_file)
                            self.pipeline.state['split']['summary_sections'] += 1
                            logger.info(f"Successfully wrote summary section for {main_file_name}")
                        except Exception as e:
                            logger.error(f"Failed to write summary section for {main_file_name}: {e}")
                            logger.error(traceback.format_exc())
                    
                    # Write raw notes to Raw Notes.md
                    if raw_notes:
                        raw_notes_file = output_dir / "Raw Notes.md"
                        try:
                            # Create file if it doesn't exist
                            if not raw_notes_file.exists():
                                with open(raw_notes_file, 'w', encoding='utf-8') as f:
                                    f.write("# Raw Notes\n\n")
                            
                            # Append raw notes section
                            with open(raw_notes_file, 'a', encoding='utf-8') as f:
                                f.write(f"\n## {main_file_name}\n\n")
                                f.write(raw_notes + "\n\n")
                                f.write("---\n\n")
                            
                            # Add to metadata
                            metadata.add_output_file(raw_notes_file)
                            self.output_files.add(raw_notes_file)
                            self.pipeline.state['split']['raw_notes_sections'] += 1
                            logger.info(f"Successfully wrote raw notes section for {main_file_name}")
                        except Exception as e:
                            logger.error(f"Failed to write raw notes section for {main_file_name}: {e}")
                            logger.error(traceback.format_exc())
                    
                except Exception as e:
                    logger.error(f"Failed to process main file {file_path}: {e}")
                    logger.error(traceback.format_exc())
                    self.pipeline.state['split']['failed_files'].add(file_path)
                    return None
                
                # Mark file as successful
                self.pipeline.state['split']['successful_files'].add(file_path)
            else:
                # This is an attachment file
                logger.debug(f"Using directory name for attachment: {parent_dir} (from {file_path})")
                # Use parent directory name as main file name
                main_file_name = parent_dir
                # Add this attachment to the main file's list
                if main_file_name not in self.attachments_by_main:
                    self.attachments_by_main[main_file_name] = set()
                self.attachments_by_main[main_file_name].add(file_path)
                logger.info(f"Found attachment {file_path} for main file {main_file_name}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            logger.error(traceback.format_exc())
            self.pipeline.state['split']['failed_files'].add(file_path)
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
        # Get relative path from parse directory
        parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
        rel_path = file_path.relative_to(parse_dir)
        
        # If this is an attachment (in a subdirectory), use the directory name
        if len(rel_path.parts) > 1:
            main_file_name = self._normalize_main_file_name(rel_path.parts[0])
            logger.debug(f"Using directory name for attachment: {main_file_name} (from {file_path})")
            return main_file_name
        
        # Otherwise, use the file stem
        main_file_name = self._normalize_main_file_name(file_path.stem)
        logger.debug(f"Using file stem for main file: {main_file_name} (from {file_path})")
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
            logger.info(f"Starting to process attachment: {attachment_path}")
            
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
            
            logger.info(f"Processing attachment {attachment_path} with original filename {filename}")
            
            # Read the attachment content
            try:
                attachment_content = attachment_path.read_text(encoding='utf-8')
                logger.info(f"Successfully read attachment content from {attachment_path}: {len(attachment_content)} characters")
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
            logger.info(f"Created section ID: {section_id}")
            
            # Update links in the attachment content
            try:
                attachment_content = self._update_links(attachment_content, section_id)
                logger.info(f"Successfully updated links in attachment content for {filename}")
            except Exception as e:
                logger.error(f"Failed to update links in attachment content for {filename}: {e}")
                logger.error(traceback.format_exc())
                return False
            
            # Write the attachment content with proper header
            try:
                logger.info(f"Writing attachment content for {filename}")
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
                
                logger.info(f"Successfully wrote attachment content for {filename}")
                
                # Track successful attachment
                self.successful_attachments.add(attachment_path)
                
                # Mark attachment as successful
                self.pipeline.state['split']['successful_files'].add(attachment_path)
                logger.info(f"Successfully processed attachment {filename}")
                
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