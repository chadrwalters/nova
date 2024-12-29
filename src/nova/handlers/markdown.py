"""Markdown file handler."""

import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class MarkdownHandler(BaseHandler):
    """Handler for Markdown files."""
    
    name = "markdown"
    version = "0.1.0"
    file_types = ["md"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize markdown handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.failures = {
            'copy_failures': [],
            'image_failures': [],
            'processing_failures': []
        }
    
    def _get_relative_path(self, from_path: Path, to_path: Path) -> str:
        """Get relative path from one file to another.
        
        Args:
            from_path: Path to start from.
            to_path: Path to end at.
            
        Returns:
            Relative path from from_path to to_path.
        """
        # Get relative path from markdown file to original file
        try:
            rel_path = os.path.relpath(to_path, from_path.parent)
            return rel_path.replace("\\", "/")  # Normalize path separators
        except ValueError:
            # If paths are on different drives, use absolute path
            return str(to_path).replace("\\", "/")
    
    def _convert_heic(self, file_path: Path, output_path: Path) -> None:
        """Convert HEIC file to JPEG.
        
        Args:
            file_path: Path to HEIC file.
            output_path: Path to output JPEG file.
            
        Raises:
            ValueError: If conversion fails.
        """
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use sips to convert HEIC to JPEG
            result = subprocess.run(
                ["sips", "-s", "format", "jpeg", str(file_path), "--out", str(output_path)],
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                raise ValueError(f"sips conversion failed: {result.stderr}")
                
        except Exception as e:
            raise ValueError(f"Failed to convert HEIC to JPEG: {e}")
    
    def _copy_attachment(
        self,
        orig_path: Path,
        attachments_dir: Path,
        output_path: Path,
    ) -> Optional[str]:
        """Copy attachment to output directory and return relative path.
        
        Args:
            orig_path: Original file path.
            attachments_dir: Attachments directory.
            output_path: Output markdown file path.
            
        Returns:
            Relative path to copied attachment, or None if copy fails.
        """
        try:
            # Skip copying if we're in the parse directory
            if str(output_path).find("/phases/parse/") != -1:
                # Just return the relative path to the original file
                rel_path = self._get_relative_path(output_path, orig_path)
                return rel_path
            
            # Create attachments directory if it doesn't exist
            attachments_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle HEIC files by converting to JPEG first
            if orig_path.suffix.lower() == '.heic':
                # Create JPEG path with same name but .jpg extension
                jpeg_path = attachments_dir / f"{orig_path.stem}.jpg"
                try:
                    # Convert HEIC to JPEG
                    self._convert_heic(orig_path, jpeg_path)
                    # Get relative path to the JPEG
                    rel_path = self._get_relative_path(output_path, jpeg_path)
                    return rel_path
                except Exception as e:
                    error_msg = f"Failed to convert HEIC to JPEG: {str(e)}"
                    self.failures['image_failures'].append(error_msg)
                    self.logger.error(error_msg)
                    return None
            
            # For non-HEIC files, copy as normal
            attachment_path = attachments_dir / orig_path.name
            shutil.copy2(orig_path, attachment_path)
            
            # Get relative path from markdown to attachment
            rel_path = self._get_relative_path(output_path, attachment_path)
            return rel_path
                
        except Exception as e:
            error_msg = f"Failed to copy {orig_path.name}: {str(e)}"
            self.failures['copy_failures'].append(error_msg)
            self.logger.error(error_msg)
            return None
    
    def _process_attachments(
        self,
        content: str,
        file_path: Path,
        output_dir: Path,
        output_path: Path,
    ) -> str:
        """Process attachments in markdown content.
        
        Args:
            content: Markdown content.
            file_path: Path to original file.
            output_dir: Output directory.
            output_path: Output markdown file path.
            
        Returns:
            Processed markdown content with updated attachment links.
        """
        # Create attachments directory using the markdown file's name
        attachments_dir = output_dir / file_path.stem
        
        # Find all links, including those with embed markers
        link_pattern = r'\* ([^[]+)\[([^\]]+)\](?:\(([^)]+)\))?(?:\s*<!--\s*{"embed":"true"}\s*-->)?'
        
        def process_match(match):
            prefix, text, path = match.groups()
            embed_marker = '<!-- {"embed":"true"} -->' if '<!-- {"embed":"true"} -->' in match.group(0) else ''
            
            # Skip if it's just an image placeholder
            if text.startswith('Image:'):
                return match.group(0)
                
            # Skip URLs
            if path and (path.startswith('http://') or path.startswith('https://')):
                return match.group(0)
                
            try:
                # Handle the file path
                if path:
                    # Unquote the path to handle URL-encoded characters
                    from urllib.parse import unquote
                    path = unquote(path)
                    orig_path = file_path.parent / path if not Path(path).is_absolute() else Path(path)
                else:
                    # Try to find the file based on the text
                    potential_name = text.split('(')[0].strip()
                    orig_path = file_path.parent / potential_name
                
                # Skip if path is a directory
                if orig_path.is_dir():
                    # Don't treat this as a failure, just skip it
                    return match.group(0)
                    
                # Verify the file exists
                if not orig_path.exists():
                    self.failures['copy_failures'].append(f"File not found: {path if path else text}")
                    return match.group(0)
                    
                # Copy attachment and get new path
                new_path = self._copy_attachment(
                    orig_path,
                    attachments_dir,
                    output_path,
                )
                
                if new_path:
                    return f'* {prefix}[{text}]({new_path}){embed_marker}'
                    
            except Exception as e:
                self.failures['copy_failures'].append(f"Failed to process {path if path else text}: {str(e)}")
                
            return match.group(0)
            
        # Process all links
        content = re.sub(link_pattern, process_match, content)
        
        return content
    
    def _process_content(self, content: str, file_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content.
            file_path: Path to original file.
            
        Returns:
            Processed markdown content.
        """
        # Process sections based on headers
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            try:
                # Check for embedded content
                embed_match = re.search(r'\[(.*?)\]\((.*?)\)<!-- \{"embed":"true"\} -->', line)
                if embed_match:
                    title, path = embed_match.groups()
                    # Convert relative path to absolute
                    if path.startswith("../"):
                        abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                    else:
                        abs_path = str(self.config.input_dir / path)
                    processed_lines.append(f"* {title}: [{path}]({abs_path}) <!-- {{'embed':'true'}} -->")
                    continue
                
                # Check for images
                image_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                if image_match:
                    alt, path = image_match.groups()
                    # Convert relative path to absolute
                    if path.startswith("../"):
                        abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                    else:
                        abs_path = str(self.config.input_dir / path)
                    processed_lines.append(f"![{alt}]({abs_path})")
                    continue
                
                # Check for file references
                file_match = re.search(r'\* ([^:]+):\s*\[(.*?)\]\((.*?)\)', line)
                if file_match:
                    file_type, title, path = file_match.groups()
                    # Convert relative path to absolute
                    if path.startswith("../"):
                        abs_path = str(self.config.input_dir / path.replace("../../../_NovaInput/", ""))
                    else:
                        abs_path = str(self.config.input_dir / path)
                    processed_lines.append(f"* {file_type}: [{title}]({abs_path})")
                    continue
                
                # Keep all other content unchanged
                processed_lines.append(line)
                    
            except Exception as e:
                self.logger.error(f"Failed to process line: {line}")
                self.logger.error(str(e))
                processed_lines.append(line)
        
        return "\n".join(processed_lines)

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a markdown file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Output directory.
            metadata: Document metadata.
                
        Returns:
            Updated document metadata.
        """
        try:
            # Reset failures for this run
            self.failures = {
                'copy_failures': [],
                'image_failures': [],
                'processing_failures': []
            }
            
            # Initialize metadata errors list if not already initialized
            if not hasattr(metadata, 'errors'):
                metadata.errors = []
            
            # Read markdown content
            content = self._safe_read_file(file_path)
            
            # Create output path with .parsed.md extension
            output_path = output_dir / f"{file_path.stem}.parsed.md"
            
            # Process attachments first
            processed_content = self._process_attachments(
                content,
                file_path,
                output_dir,
                output_path,
            )
            
            # Then process the content itself
            processed_content = self._process_content(processed_content, file_path)
            
            # Add failure summary if there were any issues
            if any(failures for failures in self.failures.values()):
                failure_summary = ["## Processing Failures\n"]
                
                if self.failures['copy_failures']:
                    failure_summary.extend([
                        "### Failed Attachments\n",
                        *[f"- {failure}\n" for failure in self.failures['copy_failures']],
                        "\n"
                    ])
                    
                if self.failures['image_failures']:
                    failure_summary.extend([
                        "### Failed Images\n",
                        *[f"- {failure}\n" for failure in self.failures['image_failures']],
                        "\n"
                    ])
                    
                if self.failures['processing_failures']:
                    failure_summary.extend([
                        "### Other Failures\n",
                        *[f"- {failure}\n" for failure in self.failures['processing_failures']],
                        "\n"
                    ])
                    
                processed_content += "\n" + "".join(failure_summary)
            
            # Write processed content using base handler's method
            self._write_markdown(output_path, file_path.stem, file_path, processed_content)
            
            # Update metadata
            metadata.processed = True
            metadata.add_output_file(output_path)
            
            # Add any failures to metadata
            if any(failures for failures in self.failures.values()):
                for failure_type, failures in self.failures.items():
                    for failure in failures:
                        metadata.add_error("markdown", failure)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Error processing markdown file: {str(e)}"
            self.failures['processing_failures'].append(error_msg)
            self.logger.error(error_msg)
            metadata.add_error("markdown", error_msg)
            metadata.processed = False
            return metadata 