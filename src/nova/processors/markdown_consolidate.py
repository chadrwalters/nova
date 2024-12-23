"""Markdown consolidation processor for merging markdown files with their attachments."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import logging
import re
import shutil
import tempfile
import time
import random
import json
import hashlib
import unicodedata
from datetime import datetime

from .base import BaseProcessor
from ..core.config import NovaConfig, ProcessorConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger
from ..core.summary import ProcessingSummary

class MarkdownConsolidateProcessor(BaseProcessor):
    """Processor for consolidating markdown files with their attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
        # Set debug logging
        self.logger.setLevel(logging.DEBUG)
        
        # Get attachment markers from config
        consolidate_config = self.config.options.get('components', {}).get('consolidate_processor', {}).get('config', {})
            
        if not consolidate_config or "attachment_markers" not in consolidate_config:
            self.logger.error("Missing consolidate_processor configuration")
            raise ProcessingError("Missing consolidate_processor configuration")
            
        self.attachment_start = consolidate_config["attachment_markers"]["start"]
        self.attachment_end = consolidate_config["attachment_markers"]["end"]
        
        # Compile regex patterns for attachment blocks
        self.attachment_start_pattern = re.compile(r'--==ATTACHMENT_BLOCK: (.+?)==--')
        self.attachment_end_pattern = re.compile(r'--==ATTACHMENT_BLOCK_END==--')
        
        # Track missing assets
        self.missing_assets: Set[str] = set()
        
        self.logger.info(f"Initialized with attachment markers: {self.attachment_start}, {self.attachment_end}")

    @staticmethod
    def _get_stable_hash(content: str, is_base64: bool = False) -> str:
        """Generate a stable hash for content.
        
        Args:
            content: Content to hash
            is_base64: Whether the content is base64 data
            
        Returns:
            Stable hash string
        """
        try:
            # For base64 data:
            # 1. Remove all whitespace and newlines
            # 2. Extract just the base64 part after the comma if it's a data URI
            # 3. Normalize to consistent format
            cleaned = ''.join(content.split())
            
            if is_base64:
                # Handle data URIs consistently
                if ',' in cleaned:
                    # Extract just the base64 data after the comma
                    cleaned = cleaned.split(',', 1)[1]
                # Remove any padding = signs from the end
                cleaned = cleaned.rstrip('=')
                # Convert to lowercase to normalize case
                cleaned = cleaned.lower()
                # Take first 1000 chars of base64 data for consistent length
                cleaned = cleaned[:1000] if len(cleaned) > 1000 else cleaned
            else:
                # For filenames and content:
                # 1. Convert to lowercase
                # 2. Replace Windows line endings
                # 3. Strip whitespace
                # 4. Normalize Unicode
                # 5. Replace URL-encoded characters
                from urllib.parse import unquote
                cleaned = unquote(cleaned)
                cleaned = cleaned.lower()
                cleaned = cleaned.replace('\r\n', '\n')
                cleaned = cleaned.strip()
                cleaned = unicodedata.normalize('NFKD', cleaned)
                # Remove any non-alphanumeric characters for filenames only
                if len(cleaned) < 1000:  # Assume it's a filename if short
                    cleaned = ''.join(c for c in cleaned if c.isalnum())
                else:
                    # For longer content, normalize whitespace and take first 1000 chars
                    cleaned = ' '.join(cleaned.split())[:1000]
            
            # Use SHA-256 for stable hashing
            hasher = hashlib.sha256()
            hasher.update(cleaned.encode('utf-8'))
            
            # Convert to integer and take modulo to get consistent length number
            hash_int = int(hasher.hexdigest(), 16)
            return str(hash_int % 10**10).zfill(10)
            
        except Exception as e:
            # If any part fails, fall back to basic hash of original content
            hasher = hashlib.sha256()
            hasher.update(str(content).encode('utf-8'))
            hash_int = int(hasher.hexdigest(), 16)
            return str(hash_int % 10**10).zfill(10)

    @staticmethod
    def _sanitize_input_path(path_str: str) -> str:
        """Sanitize input path string to handle data URIs and other problematic paths."""
        # Check if this is a data URI path
        if 'data:' in path_str:
            # Extract the part before data: if it exists
            parts = path_str.split('data:')
            base_path = parts[0].strip()
            if base_path:
                return base_path
            
            # If no base path, generate a safe name using stable hash
            content_hash = MarkdownConsolidateProcessor._get_stable_hash(path_str)
            return f"embedded_content_{content_hash}.md"
        
        return path_str

    def __call__(self, input_path: str, *args, **kwargs) -> None:
        """Override call to sanitize input path before processing."""
        self.logger.debug(f"Original input path: {input_path}")
        sanitized_path = self._sanitize_input_path(input_path)
        self.logger.debug(f"Sanitized input path: {sanitized_path}")
        
        # Convert to Path object after sanitization
        input_file = Path(sanitized_path)
        
        if not input_file.exists():
            self.logger.error(f"Input file does not exist: {input_file}")
            raise ProcessingError(f"Input file does not exist: {input_file}")
        
        return super().__call__(str(input_file), *args, **kwargs)
        
    def _setup(self) -> None:
        """Setup processor requirements."""
        # No special setup needed for consolidation
        pass
        
    def _has_attachment_markers(self, content: str) -> bool:
        """Check if content already has attachment markers."""
        # Check for any type of attachment markers
        markers = [
            '--==ATTACHMENT_BLOCK:',  # Standard marker
            '--==ATTACHMENT_BLOCK_END==--',  # Standard end marker
            self.attachment_start.format(filename='').split('{')[0],  # Formatted marker start
            self.attachment_end  # Formatted marker end
        ]
        
        # Check if any line contains any of the markers
        for line in content.splitlines():
            if any(marker in line for marker in markers):
                self.logger.debug(f"Found attachment marker: {line.strip()}")
                return True
        
        self.logger.debug("No attachment markers found")
        return False
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read()
                return False
        except UnicodeDecodeError:
            return True
    
    def _extract_base64_content(self, data_uri: str, output_path: Path) -> bool:
        """Extract and save base64 content to a file."""
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract base64 data
            base64_data = data_uri.split(',')[1]
            
            # Decode and write binary data
            import base64
            binary_data = base64.b64decode(base64_data)
            
            with open(output_path, 'wb') as f:
                f.write(binary_data)
            
            self.logger.debug(f"Successfully extracted base64 content to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract base64 content: {str(e)}")
            return False

    def _get_stable_hash(self, content: str) -> str:
        """Generate a stable hash for content."""
        # Use SHA-256 for stable hashing
        hasher = hashlib.sha256()
        hasher.update(content.encode('utf-8'))
        # Return first 8 characters of hex digest
        return hasher.hexdigest()[:8]

    def _unify_to_standard_attachments(self, content: str) -> str:
        """Unify all attachments to use standard markers."""
        self.logger.debug("Starting attachment unification")
        
        # First pass: normalize line endings to ensure consistent processing
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure links and URLs stay on single lines
        content = re.sub(r'\[([^\]]+)\]\(\s*\n\s*([^)]+)\)', r'[\1](\2)', content)
        content = re.sub(r'<\s*\n\s*([^>]+)\s*\n\s*>', r'<\1>', content)
        
        # First handle data URI images
        data_uri_pattern = r'!\[([^\]]*)\]\((data:image/[^;]+;base64,[A-Za-z0-9+/\n\s]+={0,2})\)'
        matches = list(re.finditer(data_uri_pattern, content, re.MULTILINE | re.DOTALL))
        
        # Track processed images to avoid duplicates
        processed_images = {}
        
        for match in reversed(matches):
            try:
                alt_text = match.group(1)
                data_uri = match.group(2)
                self.logger.debug(f"Processing data URI image with alt text: {alt_text}")
                
                # Clean up the data URI by removing whitespace
                data_uri = ''.join(data_uri.split())
                
                # Generate stable hash for the data URI
                content_hash = self._get_stable_hash(data_uri)
                
                if content_hash in processed_images:
                    filename = processed_images[content_hash]
                    self.logger.debug(f"Reusing existing filename for duplicate image: {filename}")
                else:
                    # Extract mime type and generate filename
                    mime_type = data_uri.split(';')[0].split('/')[-1].lower()
                    if mime_type in ['jpeg', 'heic']:
                        mime_type = 'jpg'
                    
                    filename = f"embedded_image_{content_hash}.{mime_type}"
                    processed_images[content_hash] = filename
                    
                    # Extract and save the base64 content
                    output_path = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR')) / filename
                    if not self._extract_base64_content(data_uri, output_path):
                        self.logger.error(f"Failed to extract base64 content for {filename}")
                        content = content[:match.start()] + self._process_image_reference(filename, alt_text) + content[match.end():]
                        continue
                
                # Replace with standard markdown image reference and add attachment block
                content = content[:match.start()] + self._process_image_reference(filename, alt_text) + content[match.end():]
                self.logger.debug(f"Successfully processed data URI image: {filename}")
                
            except Exception as e:
                self.logger.error(f"Error processing data URI image: {str(e)}")
                continue
        
        # Then handle regular image references
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = list(re.finditer(image_pattern, content))
        
        for match in reversed(matches):
            try:
                alt_text = match.group(1)
                filename = match.group(2).strip()
                
                # Skip if this is a data URI (already handled above)
                if filename.startswith('data:'):
                    continue
                
                # URL decode the filename if needed
                try:
                    from urllib.parse import unquote
                    decoded_filename = unquote(filename)
                    if decoded_filename != filename:
                        self.logger.debug(f"Decoded filename from {filename} to {decoded_filename}")
                        filename = decoded_filename
                except Exception as e:
                    self.logger.debug(f"URL decoding failed for {filename}: {str(e)}")
                
                # Process the image reference
                content = content[:match.start()] + self._process_image_reference(filename, alt_text) + content[match.end():]
                self.logger.debug(f"Processed image reference: {filename}")
                
            except Exception as e:
                self.logger.error(f"Error processing image reference: {str(e)}")
                continue
        
        # Clean up any malformed or duplicated markers
        content = self._cleanup_attachment_markers(content)
        
        return content

    def _cleanup_attachment_markers(self, content: str) -> str:
        """Clean up any malformed or duplicated attachment markers."""
        # Find all attachment blocks
        blocks = []
        current_block = {'start': -1, 'end': -1, 'filename': None}
        
        for match in self.attachment_start_pattern.finditer(content):
            if current_block['start'] != -1:
                # Found a new start before the previous end - mark as malformed
                blocks.append(current_block)
                current_block = {'start': -1, 'end': -1, 'filename': None}
            current_block['start'] = match.start()
            current_block['filename'] = match.group(1)
        
        for match in self.attachment_end_pattern.finditer(content):
            if current_block['start'] == -1:
                # Found an end without a start - skip it
                continue
            current_block['end'] = match.end()
            blocks.append(current_block)
            current_block = {'start': -1, 'end': -1, 'filename': None}
        
        # If there's an unclosed block, add it
        if current_block['start'] != -1:
            blocks.append(current_block)
        
        # Remove duplicate blocks with the same filename
        seen_filenames = set()
        unique_blocks = []
        
        for block in blocks:
            if block['filename'] not in seen_filenames:
                seen_filenames.add(block['filename'])
                unique_blocks.append(block)
        
        # Sort blocks by position
        unique_blocks.sort(key=lambda x: x['start'])
        
        # Rebuild content with clean blocks
        new_content = []
        last_pos = 0
        
        for block in unique_blocks:
            # Add content before this block
            if block['start'] > last_pos:
                new_content.append(content[last_pos:block['start']])
            
            # Add the block with proper markers
            block_content = content[block['start']:block['end']] if block['end'] != -1 else content[block['start']:]
            if not block_content.endswith(self.attachment_end):
                block_content = block_content.rstrip() + f"\n{self.attachment_end}"
            new_content.append(block_content)
            
            last_pos = block['end'] if block['end'] != -1 else len(content)
        
        # Add any remaining content
        if last_pos < len(content):
            new_content.append(content[last_pos:])
        
        return ''.join(new_content)

    def _create_temp_copy(self, original_path: Path) -> Path:
        """Create a temporary copy of a file with a safe name.
        
        Args:
            original_path: Original file path
            
        Returns:
            Path to temporary copy
            
        Raises:
            ProcessingError: If temporary file creation fails
        """
        self.logger.debug(f"Creating temporary copy of: {original_path}")
        
        try:
            # Create a temporary file with a stable hash name
            temp_dir = Path(tempfile.gettempdir())
            
            # Read file content in binary mode to ensure consistent hashing
            with open(original_path, 'rb') as f:
                content = f.read()
            
            # Create a stable hash from both the path and content
            # Use relative path from workspace root for consistency
            try:
                workspace_root = Path(os.getenv('NOVA_BASE_DIR', ''))
                relative_path = original_path.relative_to(workspace_root)
            except (ValueError, TypeError):
                # Fall back to absolute path if relative path fails
                relative_path = original_path.absolute()
            
            # Normalize path string
            path_str = str(relative_path).lower().replace('\\', '/')
            
            # Create stable hash from normalized path and content
            content_str = content.hex()[:1000]  # Limit content length for consistency
            combined = f"{path_str}:{content_str}"
            content_hash = self._get_stable_hash(combined)
            
            # Create a stable temp file name
            safe_name = f"nova_temp_{content_hash}.md"
            temp_path = temp_dir / safe_name
            
            self.logger.debug(f"Using temporary path: {temp_path}")
            
            # Copy the original file to the temporary location
            shutil.copy2(original_path, temp_path)
            self.logger.debug(f"Successfully copied file to: {temp_path}")
            
            return temp_path
            
        except Exception as e:
            error_msg = f"Failed to create temporary copy: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Error type: {type(e)}")
            raise ProcessingError(error_msg) from e

    def _handle_missing_asset(self, asset_path: str, asset_type: str) -> str:
        """Create a detailed placeholder for missing assets."""
        self.missing_assets.add(asset_path)
        return (
            f"[MISSING {asset_type.upper()}]\n"
            f"Original path: {asset_path}\n"
            f"Please ensure the {asset_type} file exists and is accessible.\n"
            f"Time checked: {datetime.now().isoformat()}\n"
        )

    def _process_image_reference(self, filename: str, alt_text: str) -> str:
        """Process an image reference and return the standardized format with attachment blocks."""
        # Normalize the filename to use forward slashes
        filename = str(Path(filename)).replace('\\', '/')
        
        # Create the attachment block
        attachment_block = (
            f"\n\n{self.attachment_start.format(filename=filename)}\n"
            f"![{alt_text}]({filename})\n"
            f"{self.attachment_end}\n\n"
        )
        
        # Return both the inline reference and the attachment block
        return f"![{alt_text}]({filename})" + attachment_block

    def process(self, input_file: Path, output_file: Path) -> Path:
        """Process markdown file and consolidate attachments.
        
        Args:
            input_file: Input markdown file
            output_file: Output file path
            
        Returns:
            Path to output file
        """
        try:
            # Read input file
            content = input_file.read_text(encoding='utf-8')
            
            # Normalize references
            content = self._normalize_references(content)
            
            # Validate markers
            if not self._validate_markers(content):
                raise ProcessingError("Invalid attachment markers")
            
            # Find and merge attachments
            attachments_dir = self._find_attachments_dir(input_file)
            if attachments_dir:
                content = self._merge_attachments(content, attachments_dir)
            
            # Extract metadata
            metadata = self._extract_metadata(content)
            if metadata:
                self.logger.debug(f"Extracted metadata: {metadata}")
            
            # Write output file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content, encoding='utf-8')
            
            return output_file
            
        except Exception as e:
            raise ProcessingError(f"Failed to process {input_file}: {str(e)}") from e

    def _find_attachments_dir(self, file_path: Path) -> Optional[Path]:
        """Find attachments directory for file.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Path to attachments directory if found, None otherwise
        """
        # Check for directory with same name as file
        attachments_dir = file_path.parent / file_path.stem
        if attachments_dir.is_dir():
            return attachments_dir
        
        # Check for _attachments directory
        attachments_dir = file_path.parent / "_attachments"
        if attachments_dir.is_dir():
            return attachments_dir
        
        # Check for attachments directory
        attachments_dir = file_path.parent / "attachments"
        if attachments_dir.is_dir():
            return attachments_dir
        
        return None

    def _merge_attachments(self, content: str, attachments_dir: Path) -> str:
        """Merge attachments into content.
        
        Args:
            content: Original content
            attachments_dir: Path to attachments directory
            
        Returns:
            Content with attachments merged
        """
        if not attachments_dir.exists():
            return content
        
        # Get all files in attachments directory
        attachment_files = []
        for path in attachments_dir.rglob('*'):
            if path.is_file():
                attachment_files.append(path)
        
        # Sort files for consistent order
        attachment_files.sort()
        
        # Add each attachment
        for file_path in attachment_files:
            try:
                # Read attachment content
                attachment_content = file_path.read_text(encoding='utf-8')
                
                # Add attachment block
                rel_path = file_path.relative_to(attachments_dir)
                content += f"\n\n--==ATTACHMENT_BLOCK: {rel_path}==--\n"
                content += attachment_content
                content += "\n--==ATTACHMENT_BLOCK_END==--\n"
                
            except Exception as e:
                self.logger.error(f"Failed to process attachment {file_path}: {str(e)}")
                continue
                
        return content

    def _validate_markers(self, content: str) -> bool:
        """Validate attachment markers in content.
        
        Args:
            content: Content to validate
            
        Returns:
            True if markers are valid, False otherwise
        """
        # Check for balanced markers
        start_markers = re.findall(r'--==ATTACHMENT_BLOCK:\s*([^=]+?)==--', content)
        end_markers = re.findall(r'--==ATTACHMENT_BLOCK_END==--', content)
        
        if len(start_markers) != len(end_markers):
            self.logger.error("Unbalanced attachment markers")
            return False
        
        # Check for nested markers
        marker_positions = []
        for match in re.finditer(r'--==ATTACHMENT_BLOCK:\s*([^=]+?)==--|--==ATTACHMENT_BLOCK_END==--', content):
            marker_positions.append((match.group(0).startswith('--==ATTACHMENT_BLOCK:'), match.start()))
        
        stack = []
        for is_start, _ in marker_positions:
            if is_start:
                stack.append(is_start)
            elif stack:
                stack.pop()
            else:
                self.logger.error("Invalid marker nesting")
                return False
                
        return len(stack) == 0

    def _normalize_references(self, content: str) -> str:
        """Normalize attachment references.
        
        Args:
            content: Content to normalize
            
        Returns:
            Content with normalized references
        """
        # Convert old-style markers to new format
        patterns = [
            (r'\[Begin Attachment\]:\s*([^\n]+)', r'--==ATTACHMENT_BLOCK: \1==--'),
            (r'<attached\s+([^>]+)>', r'--==ATTACHMENT_BLOCK: \1==--'),
            (r'\[attachment:\s*([^\]]+)\]', r'--==ATTACHMENT_BLOCK: \1==--')
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Add end markers where missing
        content = re.sub(
            r'(--==ATTACHMENT_BLOCK:[^=]+==--(?:(?!--==ATTACHMENT_BLOCK:|--==ATTACHMENT_BLOCK_END==--).)*?)(?=--==ATTACHMENT_BLOCK:|$)',
            r'\1\n--==ATTACHMENT_BLOCK_END==--',
            content,
            flags=re.DOTALL
        )
        
        return content

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content.
        
        Args:
            content: Content to extract metadata from
            
        Returns:
            Dict of metadata
        """
        metadata = {}
        
        # Find all metadata comments
        pattern = re.compile(r'<!--\s*({.*?})\s*-->', re.DOTALL)
        
        for match in pattern.finditer(content):
            try:
                # Parse JSON metadata
                data = json.loads(match.group(1))
                metadata.update(data)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse metadata: {str(e)}")
                continue
                
        return metadata