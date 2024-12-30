"""Disassembly phase module."""

from pathlib import Path
import shutil
import logging
from typing import Optional, Tuple, Dict
from rich.console import Console
from rich.table import Table
import re

from nova.phases.base import Phase
from nova.core.metadata import FileMetadata

logger = logging.getLogger(__name__)
console = Console()

class DisassemblyPhase(Phase):
    """Phase that splits parsed markdown files into summary and raw notes components."""
    
    def __init__(self, pipeline):
        """Initialize the disassembly phase."""
        super().__init__(pipeline)
        
        # Initialize state
        self.pipeline.state['disassemble'] = {
            'successful_files': set(),
            'failed_files': set(),
            'stats': {
                'total_processed': 0,
                'summary_files': {
                    'created': 0,
                    'empty': 0,
                    'failed': 0
                },
                'raw_notes_files': {
                    'created': 0,
                    'empty': 0,
                    'failed': 0
                },
                'attachments': {
                    'copied': 0,
                    'failed': 0
                }
            }
        }
        
    def _copy_attachments(self, src_dir: Path, dest_dir: Path, base_name: str) -> None:
        """Copy attachments directory if it exists.
        
        Args:
            src_dir: Source directory containing attachments
            dest_dir: Destination directory for attachments
            base_name: Base name of the file being processed (without .parsed)
        """
        # Check for attachments directory named after the base file in parse output
        attachments_dir = src_dir / base_name
        if attachments_dir.exists() and attachments_dir.is_dir():
            try:
                # Create base name directory in destination
                dest_attachments = dest_dir / base_name
                if dest_attachments.exists():
                    shutil.rmtree(dest_attachments)
                    
                # Create the destination directory
                dest_attachments.mkdir(parents=True, exist_ok=True)
                
                # Copy all files from the directory
                for file_path in attachments_dir.iterdir():
                    if file_path.is_file():
                        # Get the base name without .parsed.md
                        if file_path.name.endswith('.parsed.md'):
                            attachment_base = file_path.stem.replace('.parsed', '')
                            # Copy to destination with .md extension
                            shutil.copy2(file_path, dest_attachments / f"{attachment_base}.md")
                        else:
                            # Copy other files (images, etc.) as is
                            shutil.copy2(file_path, dest_attachments / file_path.name)
                
                self.pipeline.state['disassemble']['stats']['attachments']['copied'] += 1
                logger.info(f"Copied attachments from {attachments_dir}")
            except Exception as e:
                self.pipeline.state['disassemble']['stats']['attachments']['failed'] += 1
                logger.error(f"Failed to copy attachments: {str(e)}")
                
        # Check for .assets directory
        assets_dir = src_dir / f"{base_name}.assets"
        if assets_dir.exists():
            try:
                # Create attachments directory if it doesn't exist
                dest_attachments = dest_dir / base_name
                dest_attachments.mkdir(parents=True, exist_ok=True)
                
                # Copy all files from assets to attachments
                for asset in assets_dir.iterdir():
                    if asset.is_file():
                        shutil.copy2(asset, dest_attachments / asset.name)
                
                self.pipeline.state['disassemble']['stats']['attachments']['copied'] += 1
                logger.info(f"Copied assets from {assets_dir}")
            except Exception as e:
                self.pipeline.state['disassemble']['stats']['attachments']['failed'] += 1
                logger.error(f"Failed to copy assets: {str(e)}")

    def _print_summary(self):
        """Print processing summary table."""
        stats = self.pipeline.state['disassemble']['stats']
        
        table = Table(title="Disassembly Phase Summary")
        
        table.add_column("Type", style="cyan")
        table.add_column("Created/Copied", justify="right", style="green")
        table.add_column("Empty", justify="right", style="yellow")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Total", justify="right")
        
        # Add summary files row
        summary_stats = stats['summary_files']
        summary_total = sum(summary_stats.values())
        table.add_row(
            "Summary Files",
            str(summary_stats['created']),
            str(summary_stats['empty']),
            str(summary_stats['failed']),
            str(summary_total)
        )
        
        # Add raw notes row
        raw_stats = stats['raw_notes_files']
        raw_total = sum(raw_stats.values())
        table.add_row(
            "Raw Notes Files",
            str(raw_stats['created']),
            str(raw_stats['empty']),
            str(raw_stats['failed']),
            str(raw_total)
        )
        
        # Add attachments row
        attach_stats = stats['attachments']
        attach_total = sum(attach_stats.values())
        table.add_row(
            "Attachments",
            str(attach_stats['copied']),
            "",  # No empty state for attachments
            str(attach_stats['failed']),
            str(attach_total)
        )

        # Add total processed row
        table.add_row(
            "Total Files",
            str(stats['total_processed']),
            "",
            str(len(self.pipeline.state['disassemble']['failed_files'])),
            str(stats['total_processed'])
        )
        
        console.print(table)
        
        # Log any failed files
        failed_files = self.pipeline.state['disassemble']['failed_files']
        if failed_files:
            logger.warning(f"Failed to process {len(failed_files)} files:")
            for file_path in failed_files:
                logger.warning(f"  - {file_path}")

    def _split_content(self, content: str) -> Tuple[str, Optional[str]]:
        """Split content into summary and raw notes if marker exists.
        
        Args:
            content: The full file content to split
            
        Returns:
            Tuple of (summary_content, raw_notes_content)
            raw_notes_content will be None if no split marker found
        """
        SPLIT_MARKER = "--==RAW NOTES==--"
        
        if SPLIT_MARKER not in content:
            return content.strip(), None
            
        parts = content.split(SPLIT_MARKER, maxsplit=1)
        summary = parts[0].strip()
        raw_notes = parts[1].strip() if len(parts) > 1 else ""
        
        return summary, raw_notes

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file through the disassembly phase."""
        try:
            # Skip non-markdown files
            if not str(file_path).endswith('.parsed.md'):
                return metadata
                
            logger.info(f"Processing {file_path}")
            
            # Update total stats
            self.pipeline.state['disassemble']['stats']['total_processed'] += 1
            
            # Get base name without .parsed.md
            base_name = file_path.stem.replace('.parsed', '')
            
            # Copy attachments directory if it exists
            self._copy_attachments(file_path.parent, output_dir, base_name)
            
            # Read content
            content = file_path.read_text(encoding='utf-8')
            
            # Split content
            summary_content, raw_notes_content = self._split_content(content)
            
            # Create output filenames
            summary_path = output_dir / f"{base_name}.summary.md"
            raw_notes_path = output_dir / f"{base_name}.rawnotes.md"
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle summary content
            stats = self.pipeline.state['disassemble']['stats']['summary_files']
            if summary_content.strip():
                stats['created'] += 1
            else:
                stats['empty'] += 1
                logger.warning(f"Empty summary content for {file_path}")
            # Always write the summary file
            summary_path.write_text(summary_content, encoding='utf-8')
            logger.debug(f"Created summary file: {summary_path}")

            # Handle raw notes content
            stats = self.pipeline.state['disassemble']['stats']['raw_notes_files']
            if raw_notes_content is not None:
                if raw_notes_content.strip():
                    raw_notes_path.write_text(raw_notes_content, encoding='utf-8')
                    stats['created'] += 1
                    logger.debug(f"Created raw notes file: {raw_notes_path}")
                else:
                    stats['empty'] += 1
                    logger.warning(f"Empty raw notes content for {file_path}")
            
            # Update metadata
            if metadata is None:
                metadata = FileMetadata(file_path)
            metadata.add_output_file(summary_path)
            if raw_notes_content is not None:
                metadata.add_output_file(raw_notes_path)
            
            # Update success tracking
            self.pipeline.state['disassemble']['successful_files'].add(file_path)
            metadata.processed = True
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            self.pipeline.state['disassemble']['stats']['summary_files']['failed'] += 1
            if raw_notes_content is not None:
                self.pipeline.state['disassemble']['stats']['raw_notes_files']['failed'] += 1
            self.pipeline.state['disassemble']['failed_files'].add(file_path)
            if metadata:
                metadata.add_error("DisassemblyPhase", str(e))
                metadata.processed = False
            return metadata

    def finalize(self):
        """Finalize the disassembly phase."""
        self._print_summary()
        logger.info("Disassembly phase complete") 