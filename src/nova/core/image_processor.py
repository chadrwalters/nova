"""Image processor for handling various image formats and operations."""

import asyncio
import base64
import hashlib
import json
import os
import tempfile
import subprocess
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from functools import wraps
import time
import psutil

import aiofiles
from openai import AsyncOpenAI
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

from .errors import ImageNotFoundError, InvalidImageFormatError, ImageProcessingError
from .logging import get_logger
from .utils.data_uri import DataURIProcessor
from .utils.file_ops import FileOperationsManager

def monitor_performance(operation_name: str):
    """Decorator to monitor performance of operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = await func(self, *args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                # Update metrics
                elapsed = end_time - start_time
                memory_used = end_memory - start_memory
                
                # Log performance metrics
                self.logger.debug(
                    f"Operation: {operation_name}, "
                    f"Elapsed: {elapsed:.2f}s, "
                    f"Memory: {memory_used / (1024 * 1024):.2f}MB, "
                    f"Success: {success}"
                )
            
            return result
        return wrapper
    return decorator

class ImageProcessor:
    """Processor for handling image operations."""
    
    def __init__(self, cache_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize image processor.
        
        Args:
            cache_dir: Optional directory for caching results
            config: Optional configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.cache_dir = cache_dir or Path.home() / '.nova' / 'cache' / 'images'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI()
        
        # Load configuration
        self.config = {
            'heic': {
                'preferred_method': 'pillow_heif',  # or 'imagemagick'
                'fallback_enabled': True,
                'quality': 85,
                'verify_output': True
            },
            'optimization': {
                'max_dimensions': (1920, 1080),
                'jpeg_quality': 85,
                'preserve_metadata': True,
                'force_rgb': True
            },
            'performance': {
                'metrics_enabled': True,
                'log_threshold_seconds': 5.0,  # Log slow operations
                'memory_threshold_mb': 100,    # Log high memory usage
                'metrics_retention_days': 7,   # Keep metrics for 7 days
                'alert_threshold_seconds': 30  # Alert on very slow operations
            }
        }
        if config:
            self.config.update(config)
        
        # Supported image formats
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.heif'}
        
        # Initialize file operations and data URI processor
        self._file_ops = FileOperationsManager()
        self.data_uri_processor = DataURIProcessor(cache_dir=cache_dir / 'data_uri' if cache_dir else None)
        
        # Initialize metrics
        self.metrics = {
            'operations': {
                'conversions': 0,
                'optimizations': 0,
                'descriptions': 0,
                'heic_conversions': 0
            },
            'errors': {
                'conversion_errors': 0,
                'optimization_errors': 0,
                'description_errors': 0,
                'heic_errors': 0
            },
            'timing': {
                'total_time': 0,
                'avg_time': 0,
                'slowest_op': 0,
                'fastest_op': float('inf')
            },
            'cache': {
                'hits': 0,
                'misses': 0,
                'size_bytes': 0
            }
        }
        
        # Track resource state
        self._initialized = False
        self._cleanup_required = False
        self._temp_files: Set[Path] = set()
        self._active_operations = 0
        self._lock = asyncio.Lock()
    
    async def __aenter__(self) -> 'ImageProcessor':
        """Initialize resources when entering context.
        
        Returns:
            self: The ImageProcessor instance
            
        Raises:
            ImageProcessingError: If initialization fails
        """
        if self._initialized:
            self.logger.warning("ImageProcessor already initialized")
            return self
            
        try:
            # Initialize file operations manager
            self._file_ops = await self._file_ops.__aenter__()
            
            # Initialize data URI processor
            self.data_uri_processor = await self.data_uri_processor.__aenter__()
            
            # Create cache directory if needed
            if not self.cache_dir.exists():
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            self._cleanup_required = True
            
            self.logger.debug("ImageProcessor initialized successfully")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ImageProcessor: {str(e)}")
            # Clean up any partially initialized resources
            await self.__aexit__(type(e), e, e.__traceback__)
            raise ImageProcessingError(f"Failed to initialize ImageProcessor: {str(e)}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up resources when exiting context.
        
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
                self.logger.warning(f"Waiting for {self._active_operations} active operations to complete")
                async with self._lock:
                    while self._active_operations > 0:
                        await asyncio.sleep(0.1)
            
            # Clean up temporary files
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    self.logger.error(f"Error cleaning up temporary file {temp_file}: {str(e)}")
            
            # Clean up file operations manager
            if hasattr(self._file_ops, '__aexit__'):
                await self._file_ops.__aexit__(exc_type, exc_val, exc_tb)
            
            # Clean up data URI processor
            if hasattr(self.data_uri_processor, '__aexit__'):
                await self.data_uri_processor.__aexit__(exc_type, exc_val, exc_tb)
            
            self._initialized = False
            self._cleanup_required = False
            self._temp_files.clear()
            self._active_operations = 0
            
            self.logger.debug("ImageProcessor cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during ImageProcessor cleanup: {str(e)}")
            if exc_type is None:
                raise ImageProcessingError(f"Error during ImageProcessor cleanup: {str(e)}")
    
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
    
    async def process_image(self, image_path: Path) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ImageNotFoundError: If file doesn't exist
            InvalidImageFormatError: If not a valid image
            ImageProcessingError: If processing fails
        """
        if not self._initialized:
            raise ImageProcessingError("ImageProcessor not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            return await super().process_image(image_path)
        finally:
            await self._complete_operation()
    
    async def process_images(self, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """Process multiple images concurrently.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            List of processing results
        """
        tasks = []
        for path in image_paths:
            task = asyncio.create_task(self._process_image_safe(path))
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def _process_image_safe(self, image_path: Path) -> Dict[str, Any]:
        """Process image with error handling.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Processing result with success status
        """
        try:
            result = await self.process_image(image_path)
            return {
                'success': True,
                'path': str(image_path),
                **result
            }
        except Exception as e:
            return {
                'success': False,
                'path': str(image_path),
                'error': str(e)
            }
    
    @monitor_performance('convert_heic')
    async def convert_heic_to_jpg(self, heic_path: Union[str, Path]) -> Path:
        """Convert HEIC image to JPG format.
        
        Args:
            heic_path: Path to HEIC image
            
        Returns:
            Path to converted JPG image
            
        Raises:
            ImageProcessingError: If conversion fails
        """
        if not HEIF_SUPPORT:
            raise ImageProcessingError("HEIC support not available. Install pillow-heif package.")
            
        try:
            # Create temporary file with .jpg extension
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = Path(tmp.name)
            
            # Convert image
            with Image.open(heic_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Save as JPEG with optimization
                img.save(temp_path, 'JPEG', quality=85, optimize=True)
            
            return temp_path
            
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise ImageProcessingError(f"Failed to convert HEIC to JPG: {str(e)}")
    
    async def generate_description(self, image_path: Path) -> str:
        """Generate description for an image using OpenAI's vision model.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Generated description
            
        Raises:
            ImageProcessingError: If description generation fails
        """
        try:
            # Convert image to base64
            base64_image = await self.image_to_base64(image_path)
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe this image in detail, focusing on its content and context."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": base64_image
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to generate image description: {str(e)}") from e
    
    @monitor_performance('optimize_image')
    async def optimize_image(self, image_path: Path, preset: Optional[str] = None) -> Path:
        """Optimize image for web use with optional preset configuration.
        
        Args:
            image_path: Path to image file
            preset: Optional preset name ('web', 'thumbnail', 'high_quality', or None for default)
            
        Returns:
            Path to optimized image
            
        Raises:
            ImageProcessingError: If optimization fails
        """
        start_time = datetime.now()
        
        try:
            # Get preset configuration
            presets = {
                'web': {
                    'max_dimensions': (1920, 1080),
                    'jpeg_quality': 85,
                    'force_rgb': True,
                    'strip_metadata': True
                },
                'thumbnail': {
                    'max_dimensions': (300, 300),
                    'jpeg_quality': 75,
                    'force_rgb': True,
                    'strip_metadata': True
                },
                'high_quality': {
                    'max_dimensions': (3840, 2160),
                    'jpeg_quality': 95,
                    'force_rgb': False,
                    'strip_metadata': False
                }
            }
            
            # Use preset or default configuration
            if preset and preset in presets:
                config = presets[preset]
            else:
                config = self.config['optimization']
            
            # Create output path with preset suffix
            suffix = f"_{preset}" if preset else "_optimized"
            output_path = image_path.parent / f"{image_path.stem}{suffix}{image_path.suffix}"
            
            # Open and optimize image
            with Image.open(image_path) as img:
                # Convert color mode if needed
                if config['force_rgb'] and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                if (img.size[0] > config['max_dimensions'][0] or 
                    img.size[1] > config['max_dimensions'][1]):
                    img.thumbnail(config['max_dimensions'], Image.Resampling.LANCZOS)
                
                # Prepare save arguments
                save_args = {'optimize': True}
                
                # Add format-specific options
                if image_path.suffix.lower() in ['.jpg', '.jpeg']:
                    save_args['quality'] = config['jpeg_quality']
                    save_args['format'] = 'JPEG'
                elif image_path.suffix.lower() == '.png':
                    save_args['format'] = 'PNG'
                    if img.mode == 'RGB':
                        # Use optimize level 6 for RGB PNGs
                        save_args['optimize'] = 6
                elif image_path.suffix.lower() == '.webp':
                    save_args['format'] = 'WEBP'
                    save_args['quality'] = config['jpeg_quality']
                    save_args['method'] = 6  # Higher quality compression
                
                # Save optimized image
                img.save(output_path, **save_args)
            
            # Update metrics
            end_time = datetime.now()
            self.metrics['total_processing_time'] += (end_time - start_time).total_seconds()
            
            # Get optimization results
            original_size = image_path.stat().st_size
            optimized_size = output_path.stat().st_size
            compression_ratio = (1 - (optimized_size / original_size)) * 100
            
            self.logger.info(
                f"Optimized image: {image_path.name} -> {output_path.name} "
                f"(Size reduced by {compression_ratio:.1f}%)"
            )
            
            return output_path
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to optimize image: {str(e)}") from e
    
    @monitor_performance('extract_metadata')
    async def extract_metadata(self, image_path: Path) -> Dict[str, Any]:
        """Extract comprehensive metadata from image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary containing:
                - basic: Basic image information (format, mode, dimensions)
                - exif: EXIF metadata if available
                - file: File information (size, dates, path)
                - stats: Image statistics (histogram, color info)
                - errors: List of any non-critical extraction errors
            
        Raises:
            ImageProcessingError: If metadata extraction completely fails
        """
        start_time = datetime.now()
        result = {
            'basic': {},
            'exif': {},
            'file': {},
            'stats': {},
            'errors': []
        }
        
        try:
            # Get file information
            stat = image_path.stat()
            result['file'] = {
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'path': str(image_path),
                'filename': image_path.name,
                'extension': image_path.suffix.lower()
            }
            
            # Extract image information
            with Image.open(image_path) as img:
                # Basic information
                result['basic'] = {
                    'format': img.format.lower() if img.format else None,
                    'mode': img.mode,
                    'dimensions': img.size,
                    'width': img.width,
                    'height': img.height,
                    'aspect_ratio': round(img.width / img.height, 3) if img.height != 0 else None,
                    'num_frames': getattr(img, 'n_frames', 1),  # For animated images
                    'is_animated': getattr(img, 'is_animated', False),
                    'dpi': img.info.get('dpi'),
                    'compression': img.info.get('compression'),
                    'color_mode': self._get_color_mode_info(img)
                }
                
                # Try to extract EXIF data
                try:
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = img._getexif()
                        result['exif'] = self._process_exif_data(exif)
                    elif 'exif' in img.info:
                        result['exif'] = self._process_exif_data(img.info['exif'])
                except Exception as e:
                    result['errors'].append(f"EXIF extraction error: {str(e)}")
                
                # Calculate image statistics
                try:
                    result['stats'] = self._calculate_image_stats(img)
                except Exception as e:
                    result['errors'].append(f"Statistics calculation error: {str(e)}")
            
            # Update metrics
            end_time = datetime.now()
            self.metrics['total_processing_time'] += (end_time - start_time).total_seconds()
            
            return result
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to extract metadata: {str(e)}") from e
    
    def _get_color_mode_info(self, img: Image.Image) -> Dict[str, Any]:
        """Get detailed color mode information.
        
        Args:
            img: PIL Image object
            
        Returns:
            Dictionary containing color mode details
        """
        return {
            'mode': img.mode,
            'bands': list(img.getbands()),
            'is_rgb': img.mode in ('RGB', 'RGBA'),
            'is_grayscale': img.mode in ('L', 'LA'),
            'has_alpha': img.mode in ('RGBA', 'LA'),
            'bits_per_pixel': len(img.getbands()) * 8
        }
    
    def _process_exif_data(self, exif_data: Any) -> Dict[str, Any]:
        """Process EXIF data into a clean dictionary.
        
        Args:
            exif_data: Raw EXIF data
            
        Returns:
            Dictionary containing processed EXIF data
        """
        if not exif_data:
            return {}
        
        # Common EXIF tags we're interested in
        tags = {
            'Make': 'camera_make',
            'Model': 'camera_model',
            'DateTimeOriginal': 'date_taken',
            'ExposureTime': 'exposure_time',
            'FNumber': 'f_number',
            'ISOSpeedRatings': 'iso',
            'FocalLength': 'focal_length',
            'ExposureProgram': 'exposure_program',
            'Flash': 'flash',
            'GPSInfo': 'gps_info',
            'Software': 'software',
            'Artist': 'artist',
            'Copyright': 'copyright'
        }
        
        result = {}
        
        try:
            for tag, key in tags.items():
                if tag in exif_data:
                    value = exif_data[tag]
                    # Clean up the value
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8').strip('\x00')
                        except UnicodeDecodeError:
                            value = str(value)
                    elif isinstance(value, tuple) and len(value) == 2:
                        # Handle rational numbers
                        if value[1] != 0:
                            value = value[0] / value[1]
                    result[key] = value
            
            # Process GPS data if available
            if 'gps_info' in result:
                gps_data = result['gps_info']
                try:
                    result['gps'] = self._process_gps_data(gps_data)
                    del result['gps_info']  # Remove raw GPS data
                except Exception:
                    pass
        except Exception as e:
            result['errors'] = str(e)
        
        return result
    
    def _process_gps_data(self, gps_info: Dict[int, Any]) -> Dict[str, Any]:
        """Process GPS EXIF data into a clean format.
        
        Args:
            gps_info: Raw GPS EXIF data
            
        Returns:
            Dictionary containing processed GPS data
        """
        def convert_to_degrees(value: tuple) -> float:
            """Convert GPS coordinates to degrees."""
            d = float(value[0][0]) / float(value[0][1])
            m = float(value[1][0]) / float(value[1][1])
            s = float(value[2][0]) / float(value[2][1])
            return d + (m / 60.0) + (s / 3600.0)
        
        try:
            latitude = convert_to_degrees(gps_info[2])
            longitude = convert_to_degrees(gps_info[4])
            
            # Account for direction
            if gps_info[1] == 'S':
                latitude = -latitude
            if gps_info[3] == 'W':
                longitude = -longitude
            
            result = {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': None,
                'timestamp': None
            }
            
            # Add altitude if available
            if 6 in gps_info:
                alt = float(gps_info[6][0]) / float(gps_info[6][1])
                if gps_info[5] == 1:  # If altitude is below sea level
                    alt = -alt
                result['altitude'] = alt
            
            # Add timestamp if available
            if 7 in gps_info:
                result['timestamp'] = gps_info[7]
            
            return result
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_image_stats(self, img: Image.Image) -> Dict[str, Any]:
        """Calculate various image statistics.
        
        Args:
            img: PIL Image object
            
        Returns:
            Dictionary containing image statistics
        """
        # Convert to RGB for consistent analysis
        if img.mode not in ('RGB', 'RGBA', 'L'):
            img = img.convert('RGB')
        
        # Get histogram
        histogram = img.histogram()
        
        # Calculate statistics
        stats = {
            'histogram': histogram,
            'mean_brightness': 0,
            'is_dark': False,
            'is_light': False,
            'dominant_colors': [],
            'color_variance': 0
        }
        
        try:
            # Calculate mean brightness
            if img.mode == 'L':
                pixels = list(img.getdata())
                mean = sum(pixels) / len(pixels)
                stats['mean_brightness'] = mean / 255.0
            else:
                r, g, b = img.split()[:3]
                r_mean = sum(r.getdata()) / (img.width * img.height)
                g_mean = sum(g.getdata()) / (img.width * img.height)
                b_mean = sum(b.getdata()) / (img.width * img.height)
                stats['mean_brightness'] = (r_mean + g_mean + b_mean) / (3 * 255.0)
            
            # Classify brightness
            stats['is_dark'] = stats['mean_brightness'] < 0.3
            stats['is_light'] = stats['mean_brightness'] > 0.7
            
            # Get dominant colors (simple method)
            if img.mode in ('RGB', 'RGBA'):
                colors = img.getcolors(img.width * img.height)
                if colors:
                    # Sort by count (most frequent first)
                    colors.sort(reverse=True)
                    # Take top 5 colors
                    stats['dominant_colors'] = [
                        {'rgb': color[1], 'count': color[0]}
                        for color in colors[:5]
                    ]
            
            # Calculate color variance (simple method)
            if img.mode in ('RGB', 'RGBA'):
                r_var = self._calculate_variance(r.getdata())
                g_var = self._calculate_variance(g.getdata())
                b_var = self._calculate_variance(b.getdata())
                stats['color_variance'] = (r_var + g_var + b_var) / 3
        except Exception as e:
            stats['calculation_error'] = str(e)
        
        return stats
    
    def _calculate_variance(self, data: List[int]) -> float:
        """Calculate variance of a sequence of numbers.
        
        Args:
            data: List of numbers
            
        Returns:
            Variance value
        """
        n = len(data)
        if n < 2:
            return 0
        mean = sum(data) / n
        return sum((x - mean) ** 2 for x in data) / (n - 1)
    
    async def image_to_base64(self, image_path: Path) -> str:
        """Convert image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
            
        Raises:
            ImageProcessingError: If conversion fails
        """
        try:
            return await self.data_uri_processor.encode_image(image_path)
        except Exception as e:
            raise ImageProcessingError(f"Failed to convert image to base64: {str(e)}") from e
    
    async def base64_to_image(self, base64_string: str) -> Path:
        """Save base64 string as image file.
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Path to saved image file
            
        Raises:
            ImageProcessingError: If conversion fails
        """
        try:
            return await self.data_uri_processor.decode_image(base64_string)
        except Exception as e:
            raise ImageProcessingError(f"Failed to save base64 image: {str(e)}") from e
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for a file based on its path and modification time.
        
        Args:
            file_path: Path to file
            
        Returns:
            Cache key string
        """
        mtime = os.path.getmtime(file_path)
        content = f"{file_path}_{mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load cached content for a cache key.
        
        Args:
            cache_key: Cache key to look up
            
        Returns:
            Cached content if found, None otherwise
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            async with aiofiles.open(cache_file, 'r') as f:
                return json.loads(await f.read())
        return None
    
    async def _save_to_cache(self, cache_key: str, content: Dict[str, Any]) -> None:
        """Save content to cache.
        
        Args:
            cache_key: Cache key to save under
            content: Content to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        async with aiofiles.open(cache_file, 'w') as f:
            await f.write(json.dumps(content)) 