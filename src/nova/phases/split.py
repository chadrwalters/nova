"""Split phase of the Nova pipeline."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, NamedTuple
import os
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote
from datetime import datetime

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from .base import NovaPhase


logger = logging.getLogger(__name__)


class FileMetadata(NamedTuple):
    """Metadata about a parsed markdown file."""
    raw_notes_pos: int  # Position of RAW NOTES marker, or -1 if not found
    attachments: List[str]  # List of attachment references found


class SplitPhase(NovaPhase):
    """Split phase of the Nova pipeline."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize split phase.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.output_dir = None  # Will be set in process()
        
    @property
    def name(self) -> str:
        """Phase name."""
        return "split"

    def _init_consolidated_files(self):
        """Initialize the consolidated files with headers."""
        # Remove any existing files and directories in the output directory
        if self.output_dir.exists():
            for item in self.output_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

        # Create new consolidated files with headers
        (self.output_dir / "Summary.md").write_text("# Summary\n\n", encoding='utf-8')
        (self.output_dir / "Raw Notes.md").write_text("# Raw Notes\n\n", encoding='utf-8')
        (self.output_dir / "Attachments.md").write_text("# Attachments\n\n", encoding='utf-8')

    def _get_source_name(self, parsed_file: Path, parse_dir: Path) -> str:
        """Get a friendly source name from a parsed file path.
        
        Given a parsed file path and the base parse_dir, return a friendly source name.
        Strips off the trailing '.parsed.md' and converts the relative path to a string.
        
        For example, if parsed_file is:
           /.../phases/parse/20241218 - Format Test/png_test.parsed.md
        it yields:
           20241218 - Format Test/png_test
        
        Args:
            parsed_file: Path to the parsed file
            parse_dir: Base parse directory
            
        Returns:
            Friendly source name as a string
        """
        relative = parsed_file.relative_to(parse_dir)
        source_str = str(relative).replace(".parsed.md", "")
        return source_str

    def _find_attachments(self, content: str) -> List[str]:
        """Find all attachments in the content.
        
        Looks for:
        1. Embedded content with <!-- {"embed":"true"} -->
        2. Image references with ![]()
        3. File references with * Type: [title](path)
        
        Args:
            content: Content to search for attachments
            
        Returns:
            List of formatted attachment entries
        """
        attachments = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Handle embedded content
            embed_match = re.search(r'\[(.*?)\]\((.*?)\)<!-- \{"embed":"true"\} -->', line)
            if embed_match:
                title, path = embed_match.groups()
                abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                attachments.append(f"* {title}: [{path}]({abs_path})")
                continue
                
            # Handle images
            image_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
            if image_match:
                alt, path = image_match.groups()
                if path.startswith("../"):
                    abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                else:
                    abs_path = str(self.config.input_dir / path)
                attachments.append(f"* Image: [{path}]({abs_path})")
                continue
                
            # Handle other file references
            file_match = re.search(r'\* ([^:]+):\s*\[(.*?)\]\((.*?)\)', line)
            if file_match:
                file_type, title, path = file_match.groups()
                abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                attachments.append(f"* {file_type}: [{title}]({abs_path})")
                
        return attachments

    def _analyze_file(self, file_path: Path) -> FileMetadata:
        """First pass: Analyze file to find raw notes marker and attachments.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            FileMetadata with raw notes position and attachments
        """
        content = file_path.read_text(encoding='utf-8')
        raw_notes_pos = content.find("--==RAW NOTES==--")
        attachments = self._find_attachments(content)
        return FileMetadata(raw_notes_pos=raw_notes_pos, attachments=attachments)

    def _append_to_summary(self, content: str, source_name: str):
        """Append content to Summary.md with source header.
        
        Args:
            content: Content to append
            source_name: Source name for the header
        """
        if content.strip():
            with open(self.output_dir / "Summary.md", 'a', encoding='utf-8') as f:
                f.write(f"\n\n## From {source_name}\n\n")
                f.write(content.strip())

    def _append_to_raw_notes(self, content: str, source_name: str):
        """Append content to Raw Notes.md with source header.
        
        Args:
            content: Content to append
            source_name: Source name for the header
        """
        if content.strip():
            with open(self.output_dir / "Raw Notes.md", 'a', encoding='utf-8') as f:
                f.write(f"\n\n## From {source_name}\n\n")
                f.write(content.strip())

    def _append_to_attachments(self, attachments: List[str], source_name: str):
        """Append attachments to Attachments.md with source header.
        
        Args:
            attachments: List of attachment entries
            source_name: Source name for the header
        """
        if attachments:
            with open(self.output_dir / "Attachments.md", 'a', encoding='utf-8') as f:
                f.write(f"\n\n## From {source_name}\n\n")
                f.write("\n".join(attachments))

    def _process_all_parsed_files(self) -> None:
        """Process all parsed markdown files and consolidate them into output files.
        
        Uses a two-pass approach:
        1. First pass: Analyze files to find raw notes markers and attachments
        2. Second pass: Split content and write to output files
        """
        parse_dir = self.config.processing_dir / "phases" / "parse"
        if not parse_dir.exists():
            self.logger.warning(f"No parse directory found at {parse_dir}")
            return

        # Use rglob to find all .parsed.md files recursively
        parsed_files = list(parse_dir.rglob("*.parsed.md"))
        if not parsed_files:
            self.logger.warning(f"No .parsed.md files found under {parse_dir}")
            return

        self.logger.info(f"Found {len(parsed_files)} parsed files to process")

        # First pass: Analyze files
        metadata_map = {}  # file path -> FileMetadata
        for parsed_file in parsed_files:
            try:
                metadata_map[parsed_file] = self._analyze_file(parsed_file)
            except Exception as e:
                self.logger.error(f"Error analyzing {parsed_file}: {str(e)}")

        # Second pass: Process content using metadata
        for parsed_file, metadata in metadata_map.items():
            try:
                content = parsed_file.read_text(encoding='utf-8')
                source_name = self._get_source_name(parsed_file, parse_dir)

                if metadata.raw_notes_pos == -1:
                    # No raw notes marker, treat entire content as summary
                    self._append_to_summary(content, source_name)
                else:
                    # Split at raw notes marker
                    summary = content[:metadata.raw_notes_pos].strip()
                    raw_notes = content[metadata.raw_notes_pos:].strip()
                    
                    self._append_to_summary(summary, source_name)
                    self._append_to_raw_notes(raw_notes, source_name)

                # Add attachments if any were found
                if metadata.attachments:
                    self._append_to_attachments(metadata.attachments, source_name)

            except Exception as e:
                self.logger.error(f"Error processing {parsed_file}: {str(e)}")

    def _get_parse_dir(self, file_path: Path) -> Optional[Path]:
        """Get the parse directory for a file."""
        parse_dir = self.config.processing_dir / "phases" / "parse"
        if not parse_dir.exists():
            self.logger.warning(f"No parse directory found at {parse_dir}")
            return None
        return parse_dir

    async def process_file(self, file_path: Path) -> DocumentMetadata:
        """Process a single file."""
        # Get parse directory
        parse_dir = self._get_parse_dir(file_path)
        if not parse_dir:
            metadata = DocumentMetadata(
                file_name=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix[1:] if file_path.suffix else "",
                handler_name="nova",
                handler_version="0.1.0",
                processed=True,
            )
            metadata.errors.append({
                "phase": "split",
                "message": "Parse directory not found - parse phase must be run before split phase"
            })
            return metadata

        # Get output directory
        output_dir = self.config.processing_dir / "phases" / "split"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Process file
        return await self.process(file_path, output_dir)

    async def process(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None,
    ) -> DocumentMetadata:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Output directory.
            metadata: Document metadata.
                
        Returns:
            Document metadata.
        """
        try:
            # Set output directory
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize consolidated files
            self._init_consolidated_files()
            
            # Process all parsed files and consolidate them
            self._process_all_parsed_files()
            
            # Copy the input file to the output directory
            output_file = self.output_dir / file_path.name
            shutil.copy2(file_path, output_file)
            
            # Update metadata
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path,
                    self.name,
                    "0.1.0",  # Split phase version
                )
            metadata.processed = True
            metadata.add_output_file(output_file)
            metadata.add_output_file(self.output_dir / "Summary.md")
            metadata.add_output_file(self.output_dir / "Raw Notes.md")
            metadata.add_output_file(self.output_dir / "Attachments.md")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            if metadata is not None:
                metadata.add_error("split", str(e))
            return metadata 