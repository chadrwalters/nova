"""Video handler for Nova document processor."""
import mimetypes
import os
from pathlib import Path
from typing import Optional

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.core.metadata import DocumentMetadata


class VideoHandler(BaseHandler):
    """Handler for video files."""

    name = "video"
    version = "0.1.0"
    file_types = ["mp4", "mov", "avi", "mkv", "webm"]

    def __init__(self, config: ConfigManager) -> None:
        """Initialize video handler.

        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)

    def _create_video_content(self, file_path: Path) -> str:
        """Create markdown content for video file.

        Args:
            file_path: Path to video file.

        Returns:
            Markdown content.
        """
        # Create video marker
        video_marker = f"[ATTACH:VIDEO:{file_path.stem}]"

        return f"""## Video Information

{video_marker}

- **Type**: {file_path.suffix.lstrip('.')}
- **Size**: {os.path.getsize(file_path) / (1024*1024):.2f} MB

## Notes

This is a video file. The content cannot be displayed directly in markdown.
Please use an appropriate video player to view this file."""

    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a video file.

        Args:
            file_path: Path to video file.
            output_path: Path to write output.
            metadata: Document metadata.

        Returns:
            Document metadata.
        """
        try:
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update(
                {
                    "file_type": mimetypes.guess_type(file_path)[0]
                    or f"video/{file_path.suffix.lstrip('.')}",
                    "file_size": os.path.getsize(file_path),
                }
            )

            # Create content
            content = self._create_video_content(file_path)

            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path,
            )

            # Write the file
            self._safe_write_file(output_path, markdown_content)

            metadata.add_output_file(output_path)
            return metadata

        except Exception as e:
            error_msg = f"Failed to process video {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            return metadata
