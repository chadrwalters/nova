"""Parse phase for Nova document processor."""

import logging
import os
import re
from pathlib import Path
from typing import Optional
import shutil

from nova.context_processor.core.config import NovaConfig
from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.store.manager import MetadataStore
from nova.context_processor.handlers.factory import HandlerFactory
from nova.context_processor.phases.base import Phase
from nova.context_processor.utils.output_manager import OutputManager

logger = logging.getLogger(__name__)


class ParsePhase(Phase):
    """Parse phase for document processing."""

    def __init__(self, config: NovaConfig, metadata_store: MetadataStore):
        """Initialize phase.

        Args:
            config: Nova configuration
            metadata_store: Metadata store instance
        """
        super().__init__(config, metadata_store)
        self.name = "parse"
        self.version = "1.0.0"
        self.handler_factory = HandlerFactory(config)
        self.output_manager = OutputManager(config)

    def _standardize_directory_name(self, name: str) -> str:
        """Standardize directory name.
        
        Args:
            name: Original directory name
            
        Returns:
            Standardized name
        """
        # Remove any hash-based names
        if re.match(r'^[a-f0-9]{40}$', name):
            return None
            
        # Handle test files
        if name.endswith('_test') or name.startswith('test_'):
            return f"_tests/{name}"
            
        # Skip temporary/system files
        if name.startswith('.'):
            return None
            
        # For non-dated directories
        if name in ['_tests', '_templates']:
            return name
            
        # Clean up the name first
        clean_name = name.strip()
        # Replace multiple dashes/underscores with a single space
        clean_name = re.sub(r'[-_\s]+', ' ', clean_name)
        
        # Extract date if present
        date_match = re.match(r'^(\d{8})\s*-?\s*(.+)$', clean_name)
        if date_match:
            date, rest = date_match.groups()
        else:
            # For non-dated content, use today's date
            from datetime import datetime
            date = datetime.now().strftime('%Y%m%d')
            rest = clean_name
            
        # Clean up the rest of the name
        # Split into words and capitalize each word
        words = rest.split()
        # Don't capitalize certain words
        lowercase_words = {'and', 'or', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        capitalized = []
        for i, word in enumerate(words):
            # Always capitalize first and last word
            if i == 0 or i == len(words) - 1:
                capitalized.append(word.capitalize())
            # Don't capitalize certain words unless they're part of an acronym
            elif word.lower() in lowercase_words and not word.isupper():
                capitalized.append(word.lower())
            # Keep acronyms uppercase
            elif word.isupper():
                capitalized.append(word)
            # Capitalize normally
            else:
                capitalized.append(word.capitalize())
                
        rest = ' '.join(capitalized)
        
        return f"{date} - {rest}"

    def _create_standard_structure(self, dir_path: Path) -> None:
        """Create standard directory structure.
        
        Args:
            dir_path: Directory path
        """
        # Create content type directories
        content_types = {
            "documents": {".md", ".txt", ".doc", ".docx", ".pdf"},
            "spreadsheets": {".xls", ".xlsx", ".csv"},
            "presentations": {".ppt", ".pptx"},
            "images": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".heic"},
            "code": {".py", ".js", ".html", ".css", ".json", ".yaml", ".yml"},
            "data": {".json", ".xml", ".yaml", ".yml", ".csv"},
            "other": set()  # For unknown types
        }
        
        for content_type in content_types:
            (dir_path / content_type).mkdir(parents=True, exist_ok=True)
            
        # Create metadata directory
        (dir_path / "metadata").mkdir(parents=True, exist_ok=True)
        
        # Create index directory for quick lookups
        (dir_path / "index").mkdir(parents=True, exist_ok=True)

    def _get_content_type(self, file_path: Path) -> str:
        """Get content type for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Content type
        """
        ext = file_path.suffix.lower()
        content_types = {
            "documents": {".md", ".txt", ".doc", ".docx", ".pdf"},
            "spreadsheets": {".xls", ".xlsx", ".csv"},
            "presentations": {".ppt", ".pptx"},
            "images": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".heic"},
            "code": {".py", ".js", ".html", ".css", ".json", ".yaml", ".yml"},
            "data": {".json", ".xml", ".yaml", ".yml", ".csv"}
        }
        
        for content_type, extensions in content_types.items():
            if ext in extensions:
                return content_type
        return "other"

    def _create_metadata_index(self, dir_path: Path, metadata: BaseMetadata) -> None:
        """Create metadata index for quick lookups.
        
        Args:
            dir_path: Directory path
            metadata: File metadata
        """
        try:
            # Create index directory
            index_dir = dir_path / "index"
            index_dir.mkdir(parents=True, exist_ok=True)
            
            # Create content type index
            content_type = self._get_content_type(Path(metadata.file_path))
            content_type_index = index_dir / f"{content_type}_index.json"
            
            # Load existing index
            index_data = {}
            if content_type_index.exists():
                with open(content_type_index, 'r', encoding='utf-8') as f:
                    import json
                    index_data = json.load(f)
                    
            # Add metadata to index
            index_data[metadata.file_path] = {
                "title": metadata.title,
                "created_at": metadata.created_at,
                "modified_at": metadata.modified_at,
                "file_size": metadata.file_size,
                "output_dir": metadata.output_dir,
                "output_files": list(metadata.output_files)
            }
            
            # Save updated index
            with open(content_type_index, 'w', encoding='utf-8') as f:
                import json
                json.dump(index_data, f, indent=2, default=self._json_serialize)
                
        except Exception as e:
            logger.error(f"Failed to create metadata index: {str(e)}")

    def _json_serialize(self, obj):
        """JSON serializer for objects not serializable by default json code.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON serializable object
        """
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Path):
            return str(obj)
        return str(obj)  # Convert any other non-serializable objects to string

    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a single file.

        Args:
            file_path (Path): Path to file to process
            output_dir (Path): Path to output directory
            metadata (Optional[BaseMetadata]): Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata for processed file
        """
        try:
            # Get handler for file
            handler = self.handler_factory.get_handler(file_path)
            if not handler:
                logger.warning(f"No handler found for {file_path}")
                return None

            # Create standardized output directory name
            base_name = file_path.stem
            while "." in base_name:
                base_name = base_name.rsplit(".", 1)[0]
            
            std_name = self._standardize_directory_name(base_name)
            if not std_name:
                logger.warning(f"Skipping invalid directory name: {base_name}")
                return None
                
            # Get content type
            content_type = self._get_content_type(file_path)
            
            # Create output directory structure
            file_output_dir = output_dir / std_name
            file_output_dir.mkdir(parents=True, exist_ok=True)
            self._create_standard_structure(file_output_dir)

            # Parse file
            metadata = await handler.parse_file(file_path)
            if not metadata:
                logger.warning(f"Failed to parse {file_path}")
                return None

            # Write content to appropriate directory
            content_file = file_output_dir / content_type / "content.md"
            content_file.parent.mkdir(parents=True, exist_ok=True)
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(metadata.content)

            # Update metadata
            metadata.output_files.add(str(content_file))
            metadata.output_dir = str(file_output_dir)

            # Create metadata index
            self._create_metadata_index(file_output_dir, metadata)

            # Save metadata file
            metadata_file = file_output_dir / "metadata" / "metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_file, "w", encoding="utf-8") as f:
                import json
                json.dump(metadata.to_dict(), f, indent=2, default=self._json_serialize)

            return metadata

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            return None

    def finalize(self) -> None:
        """Run finalization steps."""
        try:
            # Get output directory
            output_dir = self.config.base_dir / "_NovaProcessing" / "phases" / self.name

            # Clean up any duplicate or invalid directories
            for item in output_dir.glob("*"):
                if item.is_dir():
                    std_name = self._standardize_directory_name(item.name)
                    if not std_name:
                        # Remove invalid directories
                        shutil.rmtree(item)
                        continue
                        
                    if std_name != item.name:
                        # Rename to standardized name
                        new_path = output_dir / std_name
                        if new_path.exists():
                            # If target exists, merge contents
                            self._merge_directories(item, new_path)
                            shutil.rmtree(item)
                        else:
                            # Otherwise just rename
                            item.rename(new_path)

            # Log summary
            logger.info(f"\nParsed documents")
            logger.info(f"Output directory: {output_dir}")

        except Exception as e:
            logger.error(f"Finalization failed: {str(e)}")
            raise

    def _merge_directories(self, source: Path, target: Path) -> None:
        """Merge source directory into target.
        
        Args:
            source: Source directory
            target: Target directory
        """
        try:
            # Create standard structure in target
            self._create_standard_structure(target)
            
            # Move/merge content file
            source_content = source / "content.md"
            target_content = target / "content.md"
            if source_content.exists():
                if target_content.exists():
                    # If both exist, append source to target
                    with open(source_content, 'r', encoding='utf-8') as src, \
                         open(target_content, 'a', encoding='utf-8') as dst:
                        dst.write('\n\n')  # Add separation
                        dst.write(src.read())
                else:
                    # If only source exists, move it
                    shutil.move(str(source_content), str(target_content))
                    
            # Move attachments
            source_attachments = source / "attachments"
            if source_attachments.exists():
                for item in source_attachments.rglob('*'):
                    if item.is_file():
                        # Get relative path from attachments dir
                        rel_path = item.relative_to(source_attachments)
                        dest_path = target / "attachments" / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_path.exists():
                            shutil.move(str(item), str(dest_path))
                            
        except Exception as e:
            logger.error(f"Failed to merge directories {source} into {target}: {str(e)}")
            raise

    async def process(self) -> bool:
        """Process files in phase.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get input files
            input_files = self._get_files(self.config.input_dir)
            if not input_files:
                logger.warning("No files found in input directory")
                return True

            # Get output directory
            output_dir = self.config.base_dir / "_NovaProcessing" / "phases" / self.name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create test directory if needed
            test_dir = output_dir / "_tests"
            test_dir.mkdir(exist_ok=True)

            # Process each file
            for file_path in input_files:
                try:
                    if not self.config.should_process_file(file_path):
                        logger.debug(f"Skipping {file_path}")
                        self.skipped_files.add(file_path)
                        continue

                    # Process file
                    metadata = await self.process_file(file_path, output_dir)
                    if metadata:
                        self.processed_files.add(file_path)
                    else:
                        self.failed_files.add(file_path)

                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {str(e)}")
                    self.failed_files.add(file_path)

            return True

        except Exception as e:
            logger.error(f"Phase processing failed: {str(e)}")
            return False
