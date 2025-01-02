"""Video handler for Nova document processor."""
import os
from pathlib import Path
from typing import Optional

from nova.config.manager import ConfigManager
from nova.handlers.base import BaseHandler
from nova.models.document import DocumentMetadata


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
        return f"""## Video Information

- **File**: {file_path.name}
- **Type**: {file_path.suffix.lstrip('.')}
- **Size**: {os.path.getsize(file_path) / (1024*1024):.2f} MB

## Notes

This is a video file. The content cannot be displayed directly in markdown.
Please use an appropriate video player to view this file."""
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a video file.
        
        Args:
            file_path: Path to file.
            metadata: Document metadata.
                
        Returns:
            Document metadata.
            
        Raises:
            ValueError: If file cannot be processed.
        """
        try:
            # Get output path from output manager
            output_path = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Create video content
            content = self._create_video_content(file_path)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.processed = True
            
            # Write markdown using MarkdownWriter
            self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            metadata.add_output_file(output_path)
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process video file: {file_path}")
            self.logger.error(str(e))
            if metadata:
                metadata.add_error("VideoHandler", str(e))
                metadata.processed = False
            return metadata 