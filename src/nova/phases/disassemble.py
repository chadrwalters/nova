"""Disassembly phase module."""

from pathlib import Path
import shutil
import logging
from typing import Optional, Tuple, Dict
from rich.console import Console
from rich.table import Table
import re
import traceback

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
                            dest_path = dest_attachments / f"{attachment_base}.md"
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if 'attachments' not in self.pipeline.state['disassemble']:
                                self.pipeline.state['disassemble']['attachments'] = {}
                            if base_name not in self.pipeline.state['disassemble']['attachments']:
                                self.pipeline.state['disassemble']['attachments'][base_name] = []
                            self.pipeline.state['disassemble']['attachments'][base_name].append({
                                'path': dest_path,
                                'type': 'DOC',
                                'content': file_path.read_text(encoding='utf-8')
                            })
                        else:
                            # Copy other files (images, etc.) as is
                            dest_path = dest_attachments / file_path.name
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if 'attachments' not in self.pipeline.state['disassemble']:
                                self.pipeline.state['disassemble']['attachments'] = {}
                            if base_name not in self.pipeline.state['disassemble']['attachments']:
                                self.pipeline.state['disassemble']['attachments'][base_name] = []
                            # Get file type from extension
                            file_ext = file_path.suffix.lower()
                            file_type = {
                                '.pdf': 'PDF',
                                '.doc': 'DOC',
                                '.docx': 'DOC',
                                '.xls': 'EXCEL',
                                '.xlsx': 'EXCEL',
                                '.csv': 'EXCEL',
                                '.txt': 'TXT',
                                '.json': 'JSON',
                                '.png': 'IMAGE',
                                '.jpg': 'IMAGE',
                                '.jpeg': 'IMAGE',
                                '.heic': 'IMAGE',
                                '.svg': 'IMAGE',
                                '.gif': 'IMAGE'
                            }.get(file_ext, 'OTHER')
                            try:
                                content = file_path.read_text(encoding='utf-8') if file_type not in ['IMAGE', 'PDF', 'EXCEL'] else f"Binary file: {file_path.name}"
                            except UnicodeDecodeError:
                                content = f"Binary file: {file_path.name}"
                            # Use just the file name as the key
                            attachment_key = file_path.name
                            if attachment_key.endswith('.parsed'):
                                attachment_key = attachment_key[:-7]
                            self.pipeline.state['disassemble']['attachments'][base_name].append({
                                'path': dest_path,
                                'type': file_type,
                                'content': content,
                                'id': attachment_key
                            })
                
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
                        dest_path = dest_attachments / asset.name
                        shutil.copy2(asset, dest_path)
                        # Add to pipeline state for tracking
                        if 'attachments' not in self.pipeline.state['disassemble']:
                            self.pipeline.state['disassemble']['attachments'] = {}
                        if base_name not in self.pipeline.state['disassemble']['attachments']:
                            self.pipeline.state['disassemble']['attachments'][base_name] = []
                        # Get file type from extension
                        file_ext = asset.suffix.lower()
                        file_type = {
                            '.pdf': 'PDF',
                            '.doc': 'DOC',
                            '.docx': 'DOC',
                            '.xls': 'EXCEL',
                            '.xlsx': 'EXCEL',
                            '.csv': 'EXCEL',
                            '.txt': 'TXT',
                            '.json': 'JSON',
                            '.png': 'IMAGE',
                            '.jpg': 'IMAGE',
                            '.jpeg': 'IMAGE',
                            '.heic': 'IMAGE',
                            '.svg': 'IMAGE',
                            '.gif': 'IMAGE'
                        }.get(file_ext, 'OTHER')
                        try:
                            content = asset.read_text(encoding='utf-8') if file_type not in ['IMAGE', 'PDF', 'EXCEL'] else f"Binary file: {asset.name}"
                        except UnicodeDecodeError:
                            content = f"Binary file: {asset.name}"
                        # Use just the file name as the key
                        attachment_key = asset.name
                        if attachment_key.endswith('.parsed'):
                            attachment_key = attachment_key[:-7]
                        self.pipeline.state['disassemble']['attachments'][base_name].append({
                            'path': dest_path,
                            'type': file_type,
                            'content': content,
                            'id': attachment_key
                        })
                
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
        """Process a file through the disassembly phase.
        
        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous phase
            
        Returns:
            Updated metadata if successful, None if failed
        """
        try:
            # Skip non-parsed markdown files
            if not str(file_path).endswith('.parsed.md'):
                return metadata
                
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata.from_file(
                    file_path=file_path,
                    handler_name="disassemble",
                    handler_version="1.0"
                )
                
            # Read content
            content = file_path.read_text(encoding='utf-8')
            
            # Split content into summary and raw notes
            summary_content, raw_notes_content = self._split_content(content)
            
            # Get base name without .parsed.md extension
            base_name = file_path.stem.replace('.parsed', '')
            
            # Write summary file
            if summary_content:
                summary_file = output_dir / f"{base_name}.summary.md"
                summary_file.write_text(summary_content, encoding='utf-8')
                metadata.add_output_file(summary_file)
                self.pipeline.state['disassemble']['stats']['summary_files']['created'] += 1
            else:
                self.pipeline.state['disassemble']['stats']['summary_files']['empty'] += 1
                
            # Write raw notes file if it exists
            if raw_notes_content:
                raw_notes_file = output_dir / f"{base_name}.rawnotes.md"
                raw_notes_file.write_text(raw_notes_content, encoding='utf-8')
                metadata.add_output_file(raw_notes_file)
                self.pipeline.state['disassemble']['stats']['raw_notes_files']['created'] += 1
            else:
                self.pipeline.state['disassemble']['stats']['raw_notes_files']['empty'] += 1
                
            # Copy attachments if they exist
            self._copy_attachments(file_path.parent, output_dir, base_name)
            
            # Update pipeline state
            self.pipeline.state['disassemble']['successful_files'].add(file_path)
            self.pipeline.state['disassemble']['stats']['total_processed'] += 1
            
            metadata.processed = True
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.pipeline.state['disassemble']['failed_files'].add(file_path)
            if metadata:
                metadata.add_error("DisassemblyPhase", str(e))
            return metadata

    def finalize(self):
        """Finalize the disassembly phase."""
        self._print_summary()
        logger.info("Disassembly phase complete") 