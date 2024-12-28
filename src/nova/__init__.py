"""Nova document processing system."""

__version__ = "0.1.0"

from nova.core.nova import Nova
from nova.config.manager import ConfigManager
from nova.handlers.base import BaseHandler
from nova.handlers.image import ImageHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.audio import AudioHandler
from nova.handlers.archive import ArchiveHandler
from nova.handlers.text import TextHandler
from nova.handlers.registry import HandlerRegistry
from nova.core.logging import print_summary
from pathlib import Path

__all__ = [
    "Nova",
    "ConfigManager",
    "BaseHandler",
    "ImageHandler",
    "DocumentHandler",
    "AudioHandler",
    "ArchiveHandler",
    "TextHandler",
    "HandlerRegistry",
]

class NovaPipeline:
    def __init__(self):
        self.failures = []  # Add this to track failures

    async def process_file(self, file_path: Path) -> None:
        try:
            # Existing processing code...
            if metadata is None or not metadata.processed:
                self.failures.append((
                    file_path,
                    metadata.errors[-1]["message"] if metadata and metadata.errors else "Unknown error"
                ))
        except Exception as e:
            self.failures.append((file_path, str(e)))

    async def process_directory(self, input_dir: Path) -> None:
        # Existing code...
        
        # Update the summary call to include failures
        print_summary(
            total_files=total_files,
            successful=successful,
            failed=failed,
            skipped=skipped,
            unchanged=unchanged,
            reprocessed=reprocessed,
            duration=duration,
            failures=self.failures  # Add this parameter
        )

class Nova:
    def __init__(self):
        self.failures = []  # Add this to track failures

    async def process_file(self, file_path: Path) -> None:
        try:
            # Existing processing code...
            if metadata is None or not metadata.processed:
                self.failures.append((
                    file_path,
                    metadata.errors[-1]["message"] if metadata and metadata.errors else "Unknown error"
                ))
        except Exception as e:
            self.failures.append((file_path, str(e)))

    async def process_directory(self, input_dir: Path) -> None:
        """Process all files in directory.
        
        Args:
            input_dir: Input directory path
        """
        try:
            # Existing code...
            
            # Print final summary
            print_summary(
                total_files=total_files,
                successful=successful,
                failed=failed,
                skipped=skipped,
                unchanged=unchanged,
                reprocessed=reprocessed,
                duration=duration,
                failures=self.failures  # Add this line
            )
            
        except Exception as e:
            raise NovaError(f"Pipeline failed: {str(e)}") from e