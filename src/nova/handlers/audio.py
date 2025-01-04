"""Audio handler for Nova document processor."""
import os
from pathlib import Path
from typing import Optional
import mimetypes

from nova.config.manager import ConfigManager
from nova.handlers.base import BaseHandler
from nova.models.document import DocumentMetadata


class AudioHandler(BaseHandler):
    """Handler for audio files."""
    
    name = "audio"
    version = "0.1.0"
    file_types = ["mp3", "wav", "m4a", "aac", "ogg", "flac"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize audio handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    def _create_audio_content(self, file_path: Path) -> str:
        """Create markdown content for audio file.
        
        Args:
            file_path: Path to audio file.
            
        Returns:
            Markdown content.
        """
        # Create audio marker
        audio_marker = f"[ATTACH:AUDIO:{file_path.stem}]"
        
        return f"""## Audio Information

{audio_marker}

- **Type**: {file_path.suffix.lstrip('.')}
- **Size**: {os.path.getsize(file_path) / (1024*1024):.2f} MB

## Notes

This is an audio file. The content cannot be played directly in markdown.
Please use an appropriate audio player to listen to this file."""
    
    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an audio file.
        
        Args:
            file_path: Path to audio file.
            output_path: Path to write output.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update({
                'file_type': mimetypes.guess_type(file_path)[0] or f"audio/{file_path.suffix.lstrip('.')}",
                'file_size': os.path.getsize(file_path)
            })
            
            # Create content
            content = self._create_audio_content(file_path)
            
            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Write the file
            self._safe_write_file(output_path, markdown_content)
            
            metadata.add_output_file(output_path)
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process audio {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            return metadata 