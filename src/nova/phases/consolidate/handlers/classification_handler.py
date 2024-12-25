"""Handler for classifying and organizing markdown content."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import aiofiles

from nova.phases.core.base_handler import BaseHandler
from nova.models.parsed_result import ParsedResult

class ClassificationHandler(BaseHandler):
    """Handles the classification and organization of markdown content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the classification handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.config = config or {}
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Configure output paths
        self.output_dir = Path(self.config.get('output_dir', '.'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be classified.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments (not used)
            
        Returns:
            bool: True if file has markdown extension and metadata
        """
        return (
            file_path.suffix.lower() in {'.md', '.markdown'} and
            file_path.with_suffix('.json').exists()
        )
    
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process and classify markdown content.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments (not used)
            
        Returns:
            Dict containing:
                - content: Classified markdown content
                - metadata: Classification metadata
                - processed_attachments: List of processed attachments
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'metadata': {},
            'processed_attachments': [],
            'errors': []
        }
        
        try:
            # Load classification data
            parsed_result = await self._load_classification(file_path)
            if not parsed_result:
                result['errors'].append(f"No classification data found for {file_path}")
                return result
            
            # Update attachment paths if needed
            if context.get('processed_attachments'):
                parsed_result = self._update_attachment_paths(
                    parsed_result,
                    context['processed_attachments']
                )
            
            # Save classified content
            output_path = self.output_dir / file_path.name
            await self._save_classification(output_path, parsed_result)
            
            # Update result
            result['content'] = parsed_result.combined_markdown
            result['metadata'] = parsed_result.metadata
            result['processed_attachments'] = [
                {'path': str(path)} for path in parsed_result.attachments
            ]
            
        except Exception as e:
            result['errors'].append(f"Classification failed: {str(e)}")
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'processed_attachments', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['processed_attachments'], list) and
            isinstance(result['errors'], list)
        )
    
    async def _load_classification(self, file_path: Path) -> Optional[ParsedResult]:
        """Load classification data from a markdown file's metadata."""
        try:
            # Check for metadata file
            metadata_path = file_path.with_suffix('.json')
            if not metadata_path.exists():
                self.logger.warning(f"No metadata file found for {file_path}")
                return None
            
            # Load metadata
            async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
            
            # Create ParsedResult from metadata
            return ParsedResult.from_dict(data)
        
        except Exception as e:
            self.logger.error(f"Error loading classification for {file_path}: {str(e)}")
            return None
    
    async def _save_classification(self, output_path: Path, parsed_result: ParsedResult):
        """Save the classified content."""
        try:
            base_path = output_path.with_suffix('')
            
            # Save summary blocks
            if parsed_result.summary_blocks:
                summary_path = base_path.with_name(f"{base_path.name}_summary.md")
                async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                    await f.write("\n\n".join(parsed_result.summary_blocks))
            
            # Save raw notes
            if parsed_result.raw_notes:
                notes_path = base_path.with_name(f"{base_path.name}_raw_notes.md")
                async with aiofiles.open(notes_path, 'w', encoding='utf-8') as f:
                    await f.write("\n\n".join(parsed_result.raw_notes))
            
            # Save attachments
            if parsed_result.attachments:
                attachments_path = base_path.with_name(f"{base_path.name}_attachments.md")
                async with aiofiles.open(attachments_path, 'w', encoding='utf-8') as f:
                    await f.write("\n\n".join(parsed_result.attachments))
            
            # Save metadata
            metadata_path = base_path.with_suffix('.json')
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(parsed_result.to_dict(), indent=2))
            
            self.logger.info(f"Saved classified content for: {output_path}")
        
        except Exception as e:
            self.logger.error(f"Error saving classification for {output_path}: {str(e)}")
            raise
    
    def _update_attachment_paths(self, parsed_result: ParsedResult, 
                               processed_attachments: List[Dict[str, Any]]) -> ParsedResult:
        """Update attachment paths in the ParsedResult."""
        updated = ParsedResult(
            source_file=parsed_result.source_file,
            metadata=parsed_result.metadata.copy(),
            input_file=parsed_result.input_file,
            output_file=parsed_result.output_file
        )
        
        # Create a mapping of old paths to new paths
        path_mapping = {
            attachment['original_path']: attachment['new_path']
            for attachment in processed_attachments
            if 'original_path' in attachment and 'new_path' in attachment
        }
        
        # Update paths in combined markdown
        updated.combined_markdown = parsed_result.combined_markdown
        for old_path, new_path in path_mapping.items():
            updated.combined_markdown = updated.combined_markdown.replace(
                f"]({old_path})",
                f"]({new_path})"
            )
        
        # Update paths in summary blocks
        updated.summary_blocks = []
        for block in parsed_result.summary_blocks:
            updated_block = block
            for old_path, new_path in path_mapping.items():
                updated_block = updated_block.replace(
                    f"]({old_path})",
                    f"]({new_path})"
                )
            updated.summary_blocks.append(updated_block)
        
        # Update paths in raw notes
        updated.raw_notes = []
        for note in parsed_result.raw_notes:
            updated_note = note
            for old_path, new_path in path_mapping.items():
                updated_note = updated_note.replace(
                    f"]({old_path})",
                    f"]({new_path})"
                )
            updated.raw_notes.append(updated_note)
        
        # Update attachments list
        updated.attachments = []
        for attachment in parsed_result.attachments:
            if isinstance(attachment, dict):
                updated_attachment = attachment.copy()
                if 'path' in updated_attachment and updated_attachment['path'] in path_mapping:
                    updated_attachment['path'] = path_mapping[updated_attachment['path']]
                updated.attachments.append(updated_attachment)
            else:
                updated_attachment = attachment
                for old_path, new_path in path_mapping.items():
                    updated_attachment = updated_attachment.replace(
                        f"]({old_path})",
                        f"]({new_path})"
                    )
                updated.attachments.append(updated_attachment)
        
        return updated 