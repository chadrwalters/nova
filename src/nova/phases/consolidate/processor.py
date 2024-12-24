"""Markdown consolidate processor for Nova document processor."""

import os
import re
import hashlib
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import unquote
import shutil

from ...core.pipeline.base import BaseProcessor
from ...core.config import ProcessorConfig, PipelineConfig
from ...core.errors import ProcessingError
from ...core.utils.logging import get_logger
from ...core.handlers.content_converters import ContentConverterFactory

logger = get_logger(__name__)

class ConsolidateProcessor(BaseProcessor):
    """Processor that consolidates markdown files with their attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.logger = get_logger(self.__class__.__name__)
        self.paths = pipeline_config.paths
        
        # Get configuration
        config = self.config.options.get('components', {}).get('consolidate_processor', {}).get('config', {})
        
        if not config:
            self.logger.error("Missing consolidate_processor configuration")
            raise ProcessingError("Missing consolidate_processor configuration")
            
        # Setup attachment markers
        self.attachment_markers = config.get('attachment_markers', {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        })
        
        # Setup content converter
        self.converter = ContentConverterFactory.create_converter('markdown')
        
        # Initialize stats
        self.stats = {
            'files_processed': 0,
            'attachments_processed': 0,
            'errors': 0,
            'warnings': 0
        }
        
        # Create images directory if it doesn't exist
        self.images_dir = Path(self.paths.output_dir) / 'images'
        self.images_dir.mkdir(parents=True, exist_ok=True)

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
            self.attachment_markers['start'].format(filename='').split('{')[0],  # Formatted marker start
            self.attachment_markers['end']  # Formatted marker end
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
        """Extract and save base64 content to a file.
        
        Args:
            data_uri: The data URI containing base64 content
            output_path: Path to save the extracted content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract base64 data
            # Remove whitespace and newlines from data URI
            data_uri = ''.join(data_uri.split())
            
            # Extract the base64 part after the comma
            if ',' not in data_uri:
                self.logger.error("Invalid data URI format: no comma found")
                return False
                
            base64_data = data_uri.split(',')[1]
            
            # Decode and write binary data
            try:
                binary_data = base64.b64decode(base64_data)
            except Exception as e:
                self.logger.error(f"Failed to decode base64 data: {str(e)}")
                return False
            
            with open(output_path, 'wb') as f:
                f.write(binary_data)
            
            self.logger.debug(f"Successfully extracted base64 content to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract base64 content: {str(e)}")
            return False

    def _get_stable_hash(self, content: str) -> str:
        """Generate a stable hash for content.
        
        Args:
            content: Content to hash
            
        Returns:
            First 8 characters of SHA-256 hash
        """
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
        
        # Compile regex patterns
        start_pattern = re.compile(self.attachment_markers['start'].format(filename='([^=]+?)'))
        end_pattern = re.compile(self.attachment_markers['end'])
        
        for match in start_pattern.finditer(content):
            if current_block['start'] != -1:
                # Found a new start before the previous end - mark as malformed
                blocks.append(current_block)
                current_block = {'start': -1, 'end': -1, 'filename': None}
            current_block['start'] = match.start()
            current_block['filename'] = match.group(1)
        
        for match in end_pattern.finditer(content):
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
        
        # Rebuild content with cleaned up blocks
        result = []
        last_pos = 0
        
        for block in unique_blocks:
            # Add content before block
            result.append(content[last_pos:block['start']])
            
            # Add block with proper markers
            if block['end'] != -1:
                result.append(content[block['start']:block['end']])
            else:
                # Add end marker for unclosed block
                result.append(content[block['start']:])
                result.append(f"\n{self.attachment_markers['end']}\n")
            
            last_pos = block['end'] if block['end'] != -1 else len(content)
        
        # Add remaining content
        if last_pos < len(content):
            result.append(content[last_pos:])
        
        return ''.join(result)

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
        """Process an image reference and return markdown format.
        
        Args:
            filename: Image filename
            alt_text: Alt text for the image
            
        Returns:
            Markdown image reference
        """
        # Create relative path from images directory
        image_path = self.images_dir / filename
        rel_path = os.path.relpath(str(image_path), str(self.paths.output_dir))
        
        # Return markdown image reference
        return f"![{alt_text}]({rel_path})"

    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process markdown files and consolidate with attachments.
        
        Args:
            input_path: Path to input file or directory
            output_path: Path to output directory
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Handle directory
            if input_path.is_dir():
                results = []
                for file_path in input_path.glob('**/*.md'):
                    try:
                        # Get relative path to maintain directory structure
                        rel_path = file_path.relative_to(input_path)
                        out_file = output_path / rel_path
                        
                        # Process file
                        result = self._process_file(file_path, out_file)
                        results.append(result)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process {file_path}: {str(e)}")
                        self.stats['errors'] += 1
                        results.append({
                            'input_path': str(file_path),
                            'error': str(e)
                        })
                
                return {
                    'input_path': str(input_path),
                    'output_path': str(output_path),
                    'files': results,
                    'stats': self.stats
                }
            
            # Handle single file
            return self._process_file(input_path, output_path)
            
        except Exception as e:
            context = {
                'input_path': str(input_path),
                'output_path': str(output_path)
            }
            self._handle_error(e, context)
            return {
                'error': str(e),
                'stats': self.stats
            }
            
    def _process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process a single markdown file.
        
        Args:
            input_path: Path to markdown file
            output_path: Path to output file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        if not input_path.exists():
            raise ProcessingError(f"Input file not found: {input_path}")
            
        content = input_path.read_text(encoding='utf-8')
        
        # Get output path
        output_file = self._get_output_path(str(input_path), str(output_path))
        
        # Process content
        processed_content = self._process_content(content, input_path)
        
        # Write output file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(processed_content, encoding='utf-8')
        
        self.stats['files_processed'] += 1
        
        return {
            'input_path': str(input_path),
            'output_path': str(output_file),
            'status': 'success'
        }
        
    def _process_content(self, content: str, file_path: Path) -> str:
        """Process markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to source file
            
        Returns:
            Processed content
        """
        # Skip if content already has attachment markers
        if self._has_attachment_markers(content):
            self.logger.debug("Content already has attachment markers")
            return content
            
        # Unify attachments to use standard markers
        content = self._unify_to_standard_attachments(content)
        
        return content

    def _get_output_path(self, input_path: str, output_path: str) -> Path:
        """Get output path for file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output directory
            
        Returns:
            Path to output file
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # If output_path is a directory, append input filename
        if output_path.is_dir() or not output_path.suffix:
            return output_path / input_path.name
            
        # Otherwise use output_path as is
        return output_path

    def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle error during processing.
        
        Args:
            error: Exception that occurred
            context: Dictionary with error context
        """
        self.logger.error(f"Error processing file: {str(error)}")
        self.logger.debug(f"Error context: {context}")
        self.stats['errors'] += 1
        
        if isinstance(error, ProcessingError):
            raise error
        else:
            raise ProcessingError(f"Failed to process file: {str(error)}") from error

    def _sanitize_input_path(self, input_path: str) -> str:
        """Sanitize input path.
        
        Args:
            input_path: Path to sanitize
            
        Returns:
            Sanitized path
        """
        # Convert to Path object and resolve
        path = Path(input_path).resolve()
        
        # Convert back to string with forward slashes
        return str(path).replace('\\', '/')