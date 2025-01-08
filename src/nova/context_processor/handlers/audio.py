"""Audio handler for processing audio files."""

import logging
import mimetypes
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import mutagen

from ..core.metadata import (
    BaseMetadata,
    AudioMetadata,
    MetadataFactory,
)
from .base import BaseHandler
from ..config.manager import ConfigManager

if TYPE_CHECKING:
    from ..config.manager import ConfigManager
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class AudioHandler(BaseHandler):
    """Handler for audio files."""

    def __init__(self, config: ConfigManager, pipeline: "NovaPipeline"):
        """Initialize handler.

        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        super().__init__(config, pipeline)
        self.name = "audio"
        self.version = "1.0.0"
        self.supported_extensions = [".mp3", ".wav", ".flac", ".m4a", ".aac"]

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process an audio file.

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
                    mime_type=mimetypes.guess_type(str(file_path))[0] or "audio/unknown"
                )
            # Convert to AudioMetadata if it's not already
            elif not isinstance(metadata, AudioMetadata):
                metadata = AudioMetadata(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version=self.version,
                )
                metadata.metadata = metadata.metadata  # Preserve existing metadata

            # Update base metadata
            self._update_base_metadata(file_path, metadata)

            # Extract audio information
            try:
                # Read audio file
                audio = mutagen.File(file_path)
                if not audio:
                    logger.error(f"Could not read audio file: {file_path}")
                    metadata.add_error(self.__class__.__name__, "Could not read audio file")
                    return metadata

                # Get audio properties
                info = audio.info
                metadata.duration = info.length
                metadata.sample_rate = getattr(info, "sample_rate", None)
                metadata.channels = getattr(info, "channels", None)
                metadata.bit_depth = getattr(info, "bits_per_sample", None)
                metadata.codec = audio.mime[0].split("/")[1] if hasattr(audio, "mime") else None
                metadata.bitrate = getattr(info, "bitrate", None)
                metadata.format = audio.mime[0].split("/")[1] if hasattr(audio, "mime") else None

                # Get tags
                if hasattr(audio, "tags") and audio.tags:
                    for key, value in audio.tags.items():
                        if isinstance(value, list):
                            value = value[0] if value else ""
                        value = str(value)
                        
                        # Map common tag names to metadata fields
                        key = key.lower()
                        if "artist" in key:
                            metadata.artist = value
                        elif "album" in key:
                            metadata.album = value
                        elif "track" in key and not metadata.track_number:
                            try:
                                metadata.track_number = int(value.split("/")[0])
                            except (ValueError, IndexError):
                                pass
                        elif "genre" in key:
                            metadata.genre = value
                        elif "year" in key or "date" in key:
                            try:
                                metadata.year = int(value[:4])
                            except (ValueError, IndexError):
                                pass

                # Create markdown content
                markdown_content = f"""## Audio Information
- **Original File**: {file_path.name}
- **Standardized File**: {metadata.standardized_path.name if metadata.standardized_path else 'Unknown'}
- **Duration**: {metadata.duration:.2f} seconds
- **Sample Rate**: {metadata.sample_rate or 'Unknown'} Hz
- **Channels**: {metadata.channels or 'Unknown'}
- **Bit Depth**: {metadata.bit_depth or 'Unknown'} bits
- **Codec**: {metadata.codec or 'Unknown'}
- **Bitrate**: {metadata.bitrate / 1000 if metadata.bitrate else 'Unknown'} kbps
- **Format**: {metadata.format or 'Unknown'}

## Metadata Tags
- **Artist**: {metadata.artist or 'Unknown'}
- **Album**: {metadata.album or 'Unknown'}
- **Track Number**: {metadata.track_number or 'Unknown'}
- **Genre**: {metadata.genre or 'Unknown'}
- **Year**: {metadata.year or 'Unknown'}
"""

                # Create output path
                output_path = output_dir / f"{file_path.stem}.parsed.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save content
                self._save_output(file_path, metadata, output_path, markdown_content)

                # Update metadata
                metadata.processed = True
                metadata.add_version(
                    phase="parse",
                    changes=["Processed audio file"],
                )

                return metadata

            except Exception as e:
                logger.error(f"Failed to extract audio information: {str(e)}")
                metadata.add_error(self.__class__.__name__, f"Failed to extract audio information: {str(e)}")
                return metadata

        except Exception as e:
            logger.error(f"Failed to process audio file {file_path}: {str(e)}")
            if metadata:
                metadata.add_error(self.__class__.__name__, str(e))
            return None
