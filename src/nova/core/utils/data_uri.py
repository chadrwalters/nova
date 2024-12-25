"""Data URI processing utilities."""

import base64
import hashlib
import re
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Set
from PIL import Image

from ..errors import DataURIError
from .file_ops import FileOperationsManager

class DataURIProcessor:
    """Handles processing of data URIs and base64 encoded content."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the data URI processor.
        
        Args:
            cache_dir: Optional directory for caching processed data
        """
        self.cache_dir = cache_dir
        self._file_ops = FileOperationsManager()
        
        # Initialize regex patterns
        self.data_uri_pattern = re.compile(
            r'data:(?P<mime_type>[^;,]+)?'
            r'(?P<params>(;[^,]+)*)'
            r',(?P<data>.*)'
        )
        
        # Initialize cache
        self._cache: Dict[str, Dict] = {}
        
        # Track metrics
        self.metrics = {
            'conversions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        # Track resource state
        self._initialized = False
        self._cleanup_required = False
        self._temp_files: Set[Path] = set()
        self._active_operations = 0
        self._lock = asyncio.Lock()
    
    async def _track_operation(self) -> None:
        """Track an active operation."""
        async with self._lock:
            self._active_operations += 1
    
    async def _complete_operation(self) -> None:
        """Complete an active operation."""
        async with self._lock:
            self._active_operations -= 1
    
    def _add_temp_file(self, file_path: Path) -> None:
        """Track a temporary file for cleanup.
        
        Args:
            file_path: Path to temporary file
        """
        self._temp_files.add(file_path)
    
    async def __aenter__(self) -> 'DataURIProcessor':
        """Enter async context and initialize resources.
        
        Returns:
            self: The DataURIProcessor instance
            
        Raises:
            DataURIError: If initialization fails
        """
        if self._initialized:
            return self
            
        try:
            # Initialize file operations manager
            self._file_ops = await self._file_ops.__aenter__()
            
            # Create cache directory if needed
            if self.cache_dir:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            self._cleanup_required = True
            
            return self
            
        except Exception as e:
            # Clean up any partially initialized resources
            await self.__aexit__(type(e), e, e.__traceback__)
            raise DataURIError(f"Failed to initialize DataURIProcessor: {str(e)}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and clean up resources.
        
        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if not self._cleanup_required:
            return
            
        try:
            # Wait for active operations to complete
            if self._active_operations > 0:
                async with self._lock:
                    while self._active_operations > 0:
                        await asyncio.sleep(0.1)
            
            # Clean up temporary files
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    pass  # Ignore cleanup errors
            
            # Clean up file operations manager
            if hasattr(self._file_ops, '__aexit__'):
                await self._file_ops.__aexit__(exc_type, exc_val, exc_tb)
            
            self._initialized = False
            self._cleanup_required = False
            self._temp_files.clear()
            self._active_operations = 0
            
        except Exception as e:
            if exc_type is None:
                raise DataURIError(f"Error during DataURIProcessor cleanup: {str(e)}")
    
    async def encode_file(
        self,
        file_path: Union[str, Path],
        mime_type: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """Encode a file as a data URI.
        
        Args:
            file_path: Path to the file
            mime_type: Optional MIME type (detected from file if not provided)
            use_cache: Whether to use caching
            
        Returns:
            Data URI string
            
        Raises:
            DataURIError: If encoding fails or processor not initialized
        """
        if not self._initialized:
            raise DataURIError("DataURIProcessor not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            path = Path(file_path)
            
            # Check cache first
            if use_cache and self.cache_dir:
                cache_key = self._get_cache_key(path)
                if cache_key in self._cache:
                    self.metrics['cache_hits'] += 1
                    return self._cache[cache_key]['uri']
                self.metrics['cache_misses'] += 1
            
            # Detect MIME type if not provided
            if not mime_type:
                mime_type = await self._detect_mime_type(path)
            
            # Read and encode file
            content = await self._file_ops.read_binary_file(path)
            encoded = base64.b64encode(content).decode('utf-8')
            uri = f"data:{mime_type};base64,{encoded}"
            
            # Cache result
            if use_cache and self.cache_dir:
                self._cache[self._get_cache_key(path)] = {
                    'uri': uri,
                    'mime_type': mime_type,
                    'size': len(content)
                }
            
            self.metrics['conversions'] += 1
            return uri
            
        except Exception as e:
            self.metrics['errors'] += 1
            raise DataURIError(f"Failed to encode file {file_path}: {str(e)}") from e
            
        finally:
            await self._complete_operation()
    
    async def decode_uri(
        self,
        uri: str,
        output_path: Optional[Union[str, Path]] = None,
        use_cache: bool = True
    ) -> Tuple[bytes, str]:
        """Decode a data URI to binary data.
        
        Args:
            uri: Data URI string
            output_path: Optional path to save decoded data
            use_cache: Whether to use caching
            
        Returns:
            Tuple of (decoded data, mime type)
            
        Raises:
            DataURIError: If decoding fails or processor not initialized
        """
        if not self._initialized:
            raise DataURIError("DataURIProcessor not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            # Parse URI
            match = self.data_uri_pattern.match(uri)
            if not match:
                raise DataURIError("Invalid data URI format")
            
            mime_type = match.group('mime_type') or 'application/octet-stream'
            params = match.group('params') or ''
            is_base64 = ';base64' in params
            data = match.group('data')
            
            # Decode data
            if is_base64:
                decoded = base64.b64decode(data)
            else:
                decoded = data.encode('utf-8')
            
            # Save to file if path provided
            if output_path:
                path = Path(output_path)
                await self._file_ops.create_directory(path.parent)
                await self._file_ops.write_binary_file(path, decoded)
            
            self.metrics['conversions'] += 1
            return decoded, mime_type
            
        except Exception as e:
            self.metrics['errors'] += 1
            raise DataURIError(f"Failed to decode data URI: {str(e)}") from e
            
            # Track temporary files
            if output_path:
                self._add_temp_file(Path(output_path))
            
        finally:
            await self._complete_operation()
    
    async def encode_image(
        self,
        image_path: Union[str, Path],
        format: str = 'JPEG',
        quality: int = 85,
        use_cache: bool = True
    ) -> str:
        """Convert image to data URI.
        
        Args:
            image_path: Path to image file
            format: Output format (JPEG, PNG, etc.)
            quality: Image quality (1-100, JPEG only)
            use_cache: Whether to use caching
            
        Returns:
            Data URI string
            
        Raises:
            DataURIError: If conversion fails or processor not initialized
        """
        if not self._initialized:
            raise DataURIError("DataURIProcessor not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            path = Path(image_path)
            
            # Check cache first
            if use_cache and self.cache_dir:
                cache_key = self._get_cache_key(path, {'format': format, 'quality': quality})
                if cache_key in self._cache:
                    self.metrics['cache_hits'] += 1
                    return self._cache[cache_key]['uri']
                self.metrics['cache_misses'] += 1
            
            # Process image
            with Image.open(path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Save to buffer
                buffer = BytesIO()
                img.save(buffer, format=format, quality=quality, optimize=True)
                image_data = buffer.getvalue()
                
                # Create URI
                mime_type = f"image/{format.lower()}"
                encoded = base64.b64encode(image_data).decode('utf-8')
                uri = f"data:{mime_type};base64,{encoded}"
                
                # Cache result
                if use_cache and self.cache_dir:
                    self._cache[self._get_cache_key(path, {'format': format, 'quality': quality})] = {
                        'uri': uri,
                        'mime_type': mime_type,
                        'format': format,
                        'quality': quality,
                        'size': len(image_data)
                    }
                
                self.metrics['conversions'] += 1
                return uri
                
        except Exception as e:
            self.metrics['errors'] += 1
            raise DataURIError(f"Failed to encode image {image_path}: {str(e)}") from e
            
        finally:
            await self._complete_operation()
    
    async def decode_image(
        self,
        uri: str,
        output_path: Optional[Union[str, Path]] = None,
        format: Optional[str] = None,
        use_cache: bool = True
    ) -> Path:
        """Save data URI as image file.
        
        Args:
            uri: Data URI string
            output_path: Optional path to save image
            format: Optional output format
            use_cache: Whether to use caching
            
        Returns:
            Path to saved image
            
        Raises:
            DataURIError: If decoding fails or processor not initialized
        """
        if not self._initialized:
            raise DataURIError("DataURIProcessor not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            # Decode URI
            data, mime_type = await self.decode_uri(uri)
            
            # Determine format
            if not format:
                format = mime_type.split('/')[-1].upper()
            
            # Create output path if not provided
            if not output_path:
                output_path = Path(f"temp_{hashlib.md5(uri.encode()).hexdigest()[:8]}.{format.lower()}")
            
            path = Path(output_path)
            
            # Save image
            with BytesIO(data) as buffer:
                with Image.open(buffer) as img:
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'P') and format == 'JPEG':
                        img = img.convert('RGB')
                    
                    # Save with format-specific options
                    if format == 'JPEG':
                        img.save(path, format=format, quality=85, optimize=True)
                    else:
                        img.save(path, format=format, optimize=True)
            
            self.metrics['conversions'] += 1
            return path
            
        except Exception as e:
            self.metrics['errors'] += 1
            raise DataURIError(f"Failed to decode image: {str(e)}") from e
            
            # Track temporary files
            if output_path:
                self._add_temp_file(Path(output_path))
            
        finally:
            await self._complete_operation()
    
    async def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        # Simple extension-based detection
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.json': 'application/json',
            '.pdf': 'application/pdf'
        }
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    def _get_cache_key(self, file_path: Path, params: Optional[Dict] = None) -> str:
        """Generate cache key for a file.
        
        Args:
            file_path: Path to file
            params: Optional parameters to include in key
            
        Returns:
            Cache key string
        """
        # Get file stats
        stats = file_path.stat()
        
        # Create key components
        key_parts = [
            str(file_path),
            str(stats.st_size),
            str(stats.st_mtime)
        ]
        
        # Add parameters if provided
        if params:
            key_parts.extend(f"{k}={v}" for k, v in sorted(params.items()))
        
        # Generate key
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()
    
    def get_metrics(self) -> Dict:
        """Get processing metrics.
        
        Returns:
            Dict of metrics
        """
        return self.metrics.copy()
    
    async def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        if self.cache_dir:
            await self._file_ops.remove_directory(self.cache_dir, recursive=True)
            await self._file_ops.create_directory(self.cache_dir) 
    
    async def save_base64_image(self, base64_data: str, output_path: Optional[Path] = None) -> Path:
        """Save a base64 encoded image to a file.
        
        Args:
            base64_data: Base64 encoded image data
            output_path: Optional path to save the image to. If not provided, a temporary file will be created.
            
        Returns:
            Path to the saved image
            
        Raises:
            DataURIError: If saving fails
        """
        if not self._initialized:
            raise DataURIError("DataURIProcessor not initialized. Use async with context.")
            
        async with self._lock:
            self._active_operations += 1
            try:
                # Decode base64 data
                try:
                    image_data = base64.b64decode(base64_data)
                except Exception as e:
                    raise DataURIError(f"Failed to decode base64 data: {str(e)}")
                
                # Create image from decoded data
                try:
                    image = Image.open(BytesIO(image_data))
                except Exception as e:
                    raise DataURIError(f"Failed to create image from data: {str(e)}")
                
                # Generate output path if not provided
                if output_path is None:
                    # Create hash of image data for stable filename
                    data_hash = hashlib.md5(image_data).hexdigest()[:8]
                    output_path = self.cache_dir / f"image_{data_hash}.{image.format.lower()}"
                
                # Ensure parent directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save image
                try:
                    image.save(output_path)
                    self._temp_files.add(output_path)
                    return output_path
                except Exception as e:
                    raise DataURIError(f"Failed to save image to {output_path}: {str(e)}")
                
            finally:
                self._active_operations -= 1 