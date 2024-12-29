"""Parse phase of the Nova pipeline."""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
import os

from ..config.manager import ConfigManager
from ..handlers.registry import HandlerRegistry
from ..models.document import DocumentMetadata
from ..cache.manager import CacheManager


class ParsePhase:
    """Parse phase of the Nova pipeline."""
    
    # Files to ignore
    IGNORED_FILES = {".DS_Store"}
    
    def __init__(
        self,
        config: ConfigManager,
        handler_registry: HandlerRegistry,
    ) -> None:
        """Initialize parse phase.
        
        Args:
            config: Nova configuration manager.
            handler_registry: Handler registry.
        """
        self.config = config
        self.handler_registry = handler_registry
        self.logger = logging.getLogger(__name__)
        self.cache_manager = CacheManager(config)
    
    def _write_error_markdown(self, markdown_path: Path, title: str, relative_path: str, error_msg: str) -> None:
        """Write error message to markdown file.
        
        Args:
            markdown_path: Path to markdown file.
            title: Title for markdown file.
            relative_path: Relative path to original file.
            error_msg: Error message.
        """
        # Force replacement of any invalid unicode chars in the error message
        safe_error_msg = error_msg.encode("utf-8", errors="replace").decode("utf-8")

        content = f"""# {title}

[Download Original]({relative_path})

## Error

{safe_error_msg}
"""
        # Write with UTF-8 encoding and replace any invalid characters
        with open(markdown_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(content)
    
    async def process(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None,
    ) -> DocumentMetadata:
        """Process a file."""
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get handler for file
        handler = self.handler_registry.get_handler(file_path)
        if not handler:
            raise ValueError(f"No handler found for file: {file_path}")
            
        # Process file with handler
        try:
            metadata = await handler.process(file_path, output_dir, metadata)
            if not metadata:
                metadata = DocumentMetadata(
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix[1:] if file_path.suffix else "",
                    handler_name=handler.name,
                    handler_version=handler.version,
                    processed=True,
                )
            
            # Create output file
            output_file = output_dir / f"{file_path.stem}.parsed.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(f"# {metadata.title or file_path.stem}\n\n")
                if metadata.description:
                    f.write(f"{metadata.description}\n\n")
                if "text" in metadata.metadata:
                    f.write(metadata.metadata["text"])
            
            # Add output file to metadata
            metadata.metadata.setdefault("output_files", []).append(str(output_file))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            if not metadata:
                metadata = DocumentMetadata(
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix[1:] if file_path.suffix else "",
                    handler_name="nova",
                    handler_version="0.1.0",
                    processed=False,
                )
            metadata.errors.append({
                "phase": "parse",
                "message": str(e)
            })
            
            return metadata

    async def process_file(self, file_path: Path) -> DocumentMetadata:
        """Process a single file."""
        # Get output directory
        output_dir = self.config.processing_dir / "phases" / "parse"
        
        # Process file
        return await self.process(file_path, output_dir) 