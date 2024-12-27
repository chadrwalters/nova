"""Handler for consolidating markdown files with their attachments."""

import os
from pathlib import Path
import shutil
import re
from typing import Dict, Any, Optional, List, Set

from nova.core.models.result import ProcessingResult
from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.utils.monitoring import MonitoringManager
from nova.core.models.state import HandlerState


class ConsolidationHandler(BaseHandler):
    """Handler for consolidating markdown files with their attachments."""
    
    ATTACHMENT_MARKERS = {
        "start": "--==ATTACHMENT_BLOCK: {filename}==--",
        "end": "--==ATTACHMENT_BLOCK_END==--"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.output_dir = Path(config.get("output_dir")) if config else None
        self.monitoring = MonitoringManager()
        self.monitoring.start()  # Start monitoring immediately
        self.state = HandlerState()
        
        # Additional configuration
        if config:
            self.attachment_markers = config.get("attachment_markers", self.ATTACHMENT_MARKERS)
            self.preserve_structure = config.get("preserve_structure", True)
            self.handle_attachments = config.get("handle_attachments", True)
            self.group_by_root = config.get("group_by_root", True)
        else:
            self.attachment_markers = self.ATTACHMENT_MARKERS
            self.preserve_structure = True
            self.handle_attachments = True
            self.group_by_root = True
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if the file can be handled.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file can be handled
        """
        try:
            # Only handle markdown files
            if file_path.suffix.lower() != '.md':
                return False
            
            # Check if file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                self.state.errors.append(f"File not accessible: {file_path}")
                self.monitoring.metrics["errors"] += 1
                return False
            
            return True
            
        except Exception as e:
            self.state.errors.append(f"Error checking file: {str(e)}")
            self.monitoring.metrics["errors"] += 1
            return False
    
    def _find_attachments(self, content: str) -> Set[str]:
        """Find attachment references in markdown content.
        
        Args:
            content: Markdown content to search
            
        Returns:
            Set of attachment filenames
        """
        attachments = set()
        
        # Find image references
        img_pattern = r'!\[.*?\]\((.*?)\)'
        for match in re.finditer(img_pattern, content):
            path = match.group(1)
            if path and not path.startswith(('http://', 'https://', 'ftp://')):
                attachments.add(path)
        
        # Find link references
        link_pattern = r'\[.*?\]\((.*?)\)'
        for match in re.finditer(link_pattern, content):
            path = match.group(1)
            if path and not path.startswith(('http://', 'https://', 'ftp://')):
                attachments.add(path)
        
        return attachments
    
    def _copy_attachment(self, attachment: str, source_dir: Path, output_dir: Path) -> Optional[str]:
        """Copy attachment file to output directory.
        
        Args:
            attachment: Attachment filename/path
            source_dir: Source directory
            output_dir: Output directory
            
        Returns:
            New path of attachment or None if copy failed
        """
        try:
            # Resolve attachment path
            attachment_path = source_dir / attachment
            if not attachment_path.exists():
                self.state.errors.append(f"Attachment not found: {attachment}")
                self.monitoring.metrics["errors"] += 1
                return None
            
            # Create output path preserving structure if needed
            if self.preserve_structure:
                output_path = output_dir / attachment
            else:
                output_path = output_dir / attachment_path.name
            
            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(attachment_path, output_path)
            
            # Return relative path from output directory
            return attachment if self.preserve_structure else attachment_path.name
            
        except Exception as e:
            self.state.errors.append(f"Error copying attachment {attachment}: {str(e)}")
            self.monitoring.metrics["errors"] += 1
            return None
    
    def _update_references(self, content: str, attachment_map: Dict[str, str]) -> str:
        """Update attachment references in content.
        
        Args:
            content: Original content
            attachment_map: Mapping of old paths to new paths
            
        Returns:
            Updated content
        """
        # Update image references
        for old_path, new_path in attachment_map.items():
            # Escape special regex characters in old path
            old_path_escaped = re.escape(old_path)
            
            # Update image references
            content = re.sub(
                f'!\\[([^\\]]*)\\]\\({old_path_escaped}\\)',
                f'![\\1]({new_path})',
                content
            )
            
            # Update link references
            content = re.sub(
                f'\\[([^\\]]*)\\]\\({old_path_escaped}\\)',
                f'[\\1]({new_path})',
                content
            )
        
        return content
    
    async def process(self, file_path: Path) -> ProcessingResult:
        """Process the markdown file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ProcessingResult: Processing result
        """
        if not self.output_dir:
            error = "No output directory specified"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return ProcessingResult(success=False, errors=[error])
        
        if not file_path.exists():
            error = f"File not found: {file_path}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
        
        try:
            # Start monitoring
            with self.monitoring.monitor_operation("process_markdown_file"):
                # Read markdown content
                content = file_path.read_text(encoding='utf-8')
                
                # Find attachments
                attachments = self._find_attachments(content)
                
                # Create output path preserving structure if needed
                if self.preserve_structure:
                    rel_path = file_path.relative_to(file_path.parent)
                    output_path = self.output_dir / rel_path
                else:
                    output_path = self.output_dir / file_path.name
                
                # Create parent directories
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy and process attachments
                attachment_map = {}
                if self.handle_attachments and attachments:
                    for attachment in attachments:
                        new_path = self._copy_attachment(
                            attachment,
                            file_path.parent,
                            output_path.parent
                        )
                        if new_path:
                            attachment_map[attachment] = new_path
                            
                            # Add attachment block
                            content += f"\n\n{self.attachment_markers['start'].format(filename=new_path)}\n"
                            content += f"Original: {attachment}\n"
                            content += f"{self.attachment_markers['end']}\n"
                
                # Update references
                if attachment_map:
                    content = self._update_references(content, attachment_map)
                
                # Write output file
                output_path.write_text(content, encoding='utf-8')
                
                # Update state
                self.state.processed_files.add(file_path)
                self.monitoring.metrics["files_processed"] += 1
                self.monitoring.metrics["attachments_processed"] = len(attachment_map)
                
                # Create metadata
                metadata = {
                    "original_path": str(file_path),
                    "output_path": str(output_path),
                    "attachments": list(attachment_map.values()),
                    "metrics": {
                        "attachments_found": len(attachments),
                        "attachments_processed": len(attachment_map),
                        "content_size": len(content)
                    }
                }
                
                return ProcessingResult(
                    success=True,
                    content=str(output_path),
                    metadata=metadata
                )
                
        except Exception as e:
            error = f"Error processing file {file_path}: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing result.
        
        Args:
            result: Processing result to validate
            
        Returns:
            bool: True if the result is valid
        """
        if not result.success:
            return False
            
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata:
            error = "No metadata in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("original_path"):
            error = "No original path in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("output_path"):
            error = "No output path in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up output files
            if self.output_dir and self.output_dir.exists():
                for file in self.output_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                    elif file.is_dir():
                        shutil.rmtree(file)
            
            # Stop monitoring
            self.monitoring.stop()
            
            # Update state
            self.state.end_time = self.monitoring.state["end_time"]
            
        except Exception as e:
            error = f"Error during cleanup: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1 