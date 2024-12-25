"""Manages output directory structure and file organization."""

import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

from .logging import get_logger
from .errors import FileError, with_retry, handle_errors
from .utils.file_ops import FileOperationsManager

logger = get_logger(__name__)

@dataclass
class OutputPaths:
    """Container for output directory paths."""
    
    # Base directories
    base_dir: Path
    processed_markdown: Path
    images: Path
    office: Path
    
    # Image subdirectories
    original_images: Path
    processed_images: Path
    image_metadata: Path
    image_cache: Path
    
    # Office subdirectories
    office_assets: Path
    office_temp: Path
    
    @classmethod
    def from_base(cls, base_dir: Path) -> 'OutputPaths':
        """Create OutputPaths from base directory.
        
        Args:
            base_dir: Base output directory
            
        Returns:
            Configured OutputPaths instance
        """
        return cls(
            base_dir=base_dir,
            processed_markdown=base_dir / "processed_markdown",
            images=base_dir / "images",
            office=base_dir / "office",
            original_images=base_dir / "images/original",
            processed_images=base_dir / "images/processed",
            image_metadata=base_dir / "images/metadata",
            image_cache=base_dir / "images/cache",
            office_assets=base_dir / "office/assets",
            office_temp=base_dir / "office/temp"
        )

class OutputManager:
    """Manages output directory structure and file organization."""
    
    def __init__(self, base_dir: Path):
        """Initialize output manager.
        
        Args:
            base_dir: Base output directory
        """
        self.paths = OutputPaths.from_base(base_dir)
        self._file_ops = FileOperationsManager()
        self._setup_directories()
    
    async def _setup_directories(self) -> None:
        """Create required directory structure."""
        for path in [
            self.paths.processed_markdown,
            self.paths.original_images,
            self.paths.processed_images,
            self.paths.image_metadata,
            self.paths.image_cache,
            self.paths.office_assets,
            self.paths.office_temp
        ]:
            await self._file_ops.create_directory(path)
    
    @with_retry()
    @handle_errors()
    async def save_markdown(
        self,
        content: str,
        relative_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Save processed markdown file.
        
        Args:
            content: Markdown content
            relative_path: Original file path relative to input directory
            metadata: Optional metadata to save
            
        Returns:
            Path to saved file
        """
        # Preserve directory structure
        output_path = self.paths.processed_markdown / relative_path
        await self._file_ops.create_directory(output_path.parent)
        
        # Save markdown content
        await self._file_ops.write_file(output_path, content)
        
        # Save metadata if provided
        if metadata:
            meta_path = output_path.with_suffix('.meta.json')
            await self._file_ops.write_json_file(meta_path, metadata)
        
        return output_path
    
    @with_retry()
    @handle_errors()
    async def save_image(
        self,
        image_path: Path,
        processed_image: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cache_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Path]:
        """Save image and associated data.
        
        Args:
            image_path: Path to original image
            processed_image: Optional processed image data
            metadata: Optional image metadata
            cache_data: Optional cache data (API responses etc.)
            
        Returns:
            Dictionary of saved file paths
        """
        result = {}
        
        # Save original image
        orig_path = self.paths.original_images / image_path.name
        await self._file_ops.copy_file(image_path, orig_path)
        result['original'] = orig_path
        
        # Save processed image if provided
        if processed_image:
            proc_path = self.paths.processed_images / image_path.name
            await self._file_ops.write_binary_file(proc_path, processed_image)
            result['processed'] = proc_path
        
        # Save metadata if provided
        if metadata:
            meta_path = self.paths.image_metadata / f"{image_path.stem}.meta.json"
            await self._file_ops.write_json_file(meta_path, metadata)
            result['metadata'] = meta_path
        
        # Save cache data if provided
        if cache_data:
            cache_path = self.paths.image_cache / f"{image_path.stem}.cache.json"
            await self._file_ops.write_json_file(cache_path, cache_data)
            result['cache'] = cache_path
        
        return result
    
    @with_retry()
    @handle_errors()
    async def save_office_asset(
        self,
        asset_path: Path,
        asset_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Path]:
        """Save office document asset.
        
        Args:
            asset_path: Original asset path
            asset_data: Asset binary data
            metadata: Optional asset metadata
            
        Returns:
            Dictionary of saved file paths
        """
        result = {}
        
        # Save asset
        output_path = self.paths.office_assets / asset_path.name
        await self._file_ops.create_directory(output_path.parent)
        await self._file_ops.write_binary_file(output_path, asset_data)
        result['asset'] = output_path
        
        # Save metadata if provided
        if metadata:
            meta_path = output_path.with_suffix('.meta.json')
            await self._file_ops.write_json_file(meta_path, metadata)
            result['metadata'] = meta_path
        
        return result
    
    def get_temp_path(self, prefix: str = "") -> Path:
        """Get temporary file path.
        
        Args:
            prefix: Optional filename prefix
            
        Returns:
            Path in temporary directory
        """
        temp_name = f"{prefix}{uuid.uuid4().hex}"
        return self.paths.office_temp / temp_name
    
    async def cleanup(self) -> None:
        """Clean up temporary files."""
        # Only clean temp directory
        if await self._file_ops.path_exists(self.paths.office_temp):
            await self._file_ops.remove_directory(self.paths.office_temp, recursive=True)
            await self._file_ops.create_directory(self.paths.office_temp)

__all__ = ['OutputManager', 'OutputPaths'] 