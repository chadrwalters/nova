"""Audio handler for Nova document processor."""
import os
from pathlib import Path
from typing import Optional

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
        return f"""## Audio Information

- **File**: {file_path.name}
- **Type**: {file_path.suffix.lstrip('.')}
- **Size**: {os.path.getsize(file_path) / (1024*1024):.2f} MB

## Notes

This is an audio file. The content cannot be played directly in markdown.
Please use an appropriate audio player to listen to this file."""
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an audio file.
        
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
            
            # Create audio content
            content = self._create_audio_content(file_path)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.processed = True
            
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
            self.logger.error(f"Failed to process audio file: {file_path}")
            self.logger.error(str(e))
            if metadata:
                metadata.add_error("AudioHandler", str(e))
                metadata.processed = False
            return metadata 