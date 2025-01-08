"""Video handler for processing video files."""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import cv2

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.types import VideoMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class VideoHandler(BaseHandler):
    """Handler for video files."""

    def __init__(self, config: ConfigManager):
        """Initialize video handler.
        
        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.supported_extensions = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".webm",
            ".flv",
        }

    async def _extract_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract information from a video file.

        Args:
            file_path: Path to file

        Returns:
            Optional[Dict[str, Any]]: Video information if successful, None if failed
        """
        try:
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                logger.error(f"Could not open video file: {file_path}")
                return None

            # Get video properties
            info = {
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
                "file_size": os.path.getsize(file_path),
            }

            # Calculate duration
            info["duration"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0

            return info

        except Exception as e:
            logger.error(f"Failed to extract video information: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: VideoMetadata) -> bool:
        """Process a video file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Extract video information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.fps = info["fps"]
            metadata.frame_count = info["frame_count"]
            metadata.duration = info["duration"]
            metadata.width = info["width"]
            metadata.height = info["height"]
            metadata.codec = info["codec"]
            metadata.file_size = info["file_size"]

            return True

        except Exception as e:
            logger.error(f"Failed to process video {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: VideoMetadata) -> bool:
        """Parse a video file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Extract video information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.fps = info["fps"]
            metadata.frame_count = info["frame_count"]
            metadata.duration = info["duration"]
            metadata.width = info["width"]
            metadata.height = info["height"]
            metadata.codec = info["codec"]
            metadata.file_size = info["file_size"]

            return True

        except Exception as e:
            logger.error(f"Failed to parse video {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: VideoMetadata) -> bool:
        """Disassemble a video file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble video {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: VideoMetadata) -> bool:
        """Split a video file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split video {file_path}: {e}")
            return False
