"""Archive handler for processing archive files."""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import py7zr
import rarfile

from ..core.metadata import (
    BaseMetadata,
    ArchiveMetadata,
    MetadataFactory,
)
from .base import BaseHandler
from ..config.manager import ConfigManager

if TYPE_CHECKING:
    from ..config.manager import ConfigManager
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class ArchiveHandler(BaseHandler):
    """Handler for archive files."""

    def __init__(self, config: ConfigManager, pipeline: "NovaPipeline"):
        """Initialize handler.

        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        super().__init__(config, pipeline)
        self.name = "archive"
        self.version = "1.0.0"
        self.supported_extensions = [".7z", ".rar", ".zip", ".tar", ".gz"]

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process an archive file.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Check if file extension is supported
            extension = file_path.suffix.lower()
            if extension not in self.supported_extensions:
                logger.warning(f"Unsupported file extension: {extension}")
                return None

            # Create metadata if not provided
            if not metadata:
                metadata = MetadataFactory.create(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version=self.version,
                    mime_type=mimetypes.guess_type(str(file_path))[0] or "application/x-archive"
                )
            # Convert to ArchiveMetadata if it's not already
            elif not isinstance(metadata, ArchiveMetadata):
                metadata = ArchiveMetadata(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version=self.version,
                )
                metadata.metadata = metadata.metadata  # Preserve existing metadata

            # Update base metadata
            self._update_base_metadata(file_path, metadata)

            # Extract archive information
            try:
                # Handle different archive types
                if extension == ".7z":
                    with py7zr.SevenZipFile(file_path, mode="r") as archive:
                        info = archive.archiveinfo()
                        metadata.file_count = len(archive.getnames())
                        metadata.total_size = info.uncompressed
                        metadata.compressed_size = info.compressed
                        metadata.compression_ratio = info.uncompressed / info.compressed if info.compressed > 0 else 0
                        metadata.compression_method = info.method_names[0] if info.method_names else None
                        metadata.files = list(archive.getnames())
                        metadata.directories = [
                            str(Path(f).parent) for f in metadata.files 
                            if str(Path(f).parent) != "."
                        ]
                        metadata.directories = list(set(metadata.directories))

                elif extension == ".rar":
                    with rarfile.RarFile(file_path) as archive:
                        info_list = archive.infolist()
                        metadata.file_count = len(info_list)
                        metadata.total_size = sum(f.file_size for f in info_list)
                        metadata.compressed_size = os.path.getsize(file_path)
                        metadata.compression_ratio = metadata.total_size / metadata.compressed_size if metadata.compressed_size > 0 else 0
                        metadata.compression_method = "RAR"
                        metadata.files = archive.namelist()
                        metadata.directories = [
                            str(Path(f).parent) for f in metadata.files 
                            if str(Path(f).parent) != "."
                        ]
                        metadata.directories = list(set(metadata.directories))

                else:
                    logger.warning(f"Unsupported archive type: {extension}")
                    metadata.add_error(self.__class__.__name__, f"Unsupported archive type: {extension}")
                    return metadata

                # Create markdown content
                markdown_content = f"""## Archive Information
- **Original File**: {file_path.name}
- **Standardized File**: {metadata.standardized_path.name if metadata.standardized_path else 'Unknown'}
- **File Count**: {metadata.file_count}
- **Total Size**: {metadata.total_size / 1024:.1f} KB
- **Compressed Size**: {metadata.compressed_size / 1024:.1f} KB
- **Compression Ratio**: {metadata.compression_ratio:.2f}
- **Compression Method**: {metadata.compression_method or 'Unknown'}

## Directory Structure
"""
                for directory in sorted(metadata.directories):
                    markdown_content += f"- {directory}/\n"
                    files_in_dir = [
                        Path(f).name for f in metadata.files 
                        if str(Path(f).parent) == directory
                    ]
                    for file in sorted(files_in_dir):
                        markdown_content += f"  - {file}\n"

                # Add root files
                root_files = [
                    Path(f).name for f in metadata.files 
                    if str(Path(f).parent) == "."
                ]
                if root_files:
                    markdown_content += "\n## Root Files\n"
                    for file in sorted(root_files):
                        markdown_content += f"- {file}\n"

                # Create output path
                output_path = output_dir / f"{file_path.stem}.parsed.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save content
                self._save_output(file_path, metadata, output_path, markdown_content)

                # Update metadata
                metadata.processed = True
                metadata.add_version(
                    phase="parse",
                    changes=["Processed archive file"],
                )

                return metadata

            except Exception as e:
                logger.error(f"Failed to extract archive information: {str(e)}")
                metadata.add_error(self.__class__.__name__, f"Failed to extract archive information: {str(e)}")
                return metadata

        except Exception as e:
            logger.error(f"Failed to process archive file {file_path}: {str(e)}")
            if metadata:
                metadata.add_error(self.__class__.__name__, str(e))
            return None
