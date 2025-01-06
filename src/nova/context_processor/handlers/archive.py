"""Archive handler for Nova document processor."""
import os
from pathlib import Path
from typing import Optional

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.models.document import DocumentMetadata


class ArchiveHandler(BaseHandler):
    """Handler for archive files."""

    name = "archive"
    version = "0.1.0"
    file_types = ["zip", "tar", "gz", "bz2", "7z", "rar"]

    def __init__(self, config: ConfigManager) -> None:
        """Initialize archive handler.

        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)

    def _create_archive_content(self, file_path: Path) -> str:
        """Create markdown content for archive file.

        Args:
            file_path: Path to archive file.

        Returns:
            Markdown content.
        """
        return f"""## Archive Information

- **File**: {file_path.name}
- **Type**: {file_path.suffix.lstrip('.')}
- **Size**: {os.path.getsize(file_path) / (1024*1024):.2f} MB

## Notes

This is an archive file. The contents cannot be displayed directly in markdown.
Please use an appropriate archive tool to extract and view the contents."""

    async def process_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an archive file.

        Args:
            file_path: Path to file.
            output_path: Path to output file.
            metadata: Document metadata.

        Returns:
            Document metadata.

        Raises:
            ValueError: If file cannot be processed.
        """
        try:
            # Create archive content
            content = self._create_archive_content(file_path)

            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata["original_path"] = str(file_path)
            metadata.processed = True

            # Write markdown using MarkdownWriter
            self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path,
            )

            metadata.add_output_file(output_path)
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to process archive file: {file_path}")
            self.logger.error(str(e))
            if metadata:
                metadata.add_error("ArchiveHandler", str(e))
                metadata.processed = False
            return metadata
