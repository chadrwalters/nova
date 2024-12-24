"""Handler for consolidating markdown files with their attachments."""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import aiofiles

from .base_handler import BaseConsolidateHandler
from ..config.defaults import DEFAULT_CONFIG

class ConsolidateHandler(BaseConsolidateHandler):
    """Handles consolidation of markdown files with their attachments."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the consolidation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('consolidate', {}), **(config or {})}
        
        # Initialize attachment tracking
        self.processed_attachments: Set[Path] = set()
        
        # Set up markers
        self.markers = self.config.get('attachment_markers', {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        })
    
    def can_handle(self, file_path: Path, attachments: List[Path]) -> bool:
        """Check if file is a markdown file with attachments.
        
        Args:
            file_path: Path to the markdown file
            attachments: List of potential attachments
            
        Returns:
            bool: True if file is markdown and has valid attachments
        """
        return (
            file_path.suffix.lower() == '.md' and
            bool(attachments)  # Has at least one attachment
        )
    
    async def process(self, file_path: Path, attachments: List[Path], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a markdown file and its attachments.
        
        Args:
            file_path: Path to the markdown file
            attachments: List of attachments
            context: Processing context
            
        Returns:
            Dict containing consolidated results
        """
        result = {
            'content': '',
            'processed_attachments': [],
            'metadata': {},
            'errors': []
        }
        
        try:
            # Read original content
            content = await self._read_file(file_path)
            
            # Process each attachment
            for attachment in attachments:
                try:
                    processed = await self._process_attachment(attachment, context)
                    if processed:
                        result['processed_attachments'].append(processed)
                        
                        # Add attachment block to content
                        content += f"\n\n{self.markers['start'].format(filename=attachment.name)}\n"
                        content += processed['content']
                        content += f"\n{self.markers['end']}\n"
                        
                        # Update metadata
                        if processed.get('metadata'):
                            result['metadata'][attachment.name] = processed['metadata']
                            
                except Exception as e:
                    result['errors'].append(f"Error processing attachment {attachment}: {str(e)}")
            
            result['content'] = content
            
        except Exception as e:
            result['errors'].append(f"Error consolidating {file_path}: {str(e)}")
            await self.rollback(result)
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'processed_attachments', 'metadata', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['processed_attachments'], list) and
            isinstance(result['metadata'], dict) and
            isinstance(result['errors'], list)
        )
    
    async def rollback(self, result: Dict[str, Any]) -> None:
        """Rollback any processed attachments.
        
        Args:
            result: Processing results to rollback
        """
        for attachment in result.get('processed_attachments', []):
            try:
                if 'temp_path' in attachment:
                    temp_path = Path(attachment['temp_path'])
                    if temp_path.exists():
                        temp_path.unlink()
            except Exception as e:
                print(f"Error during rollback: {str(e)}")
    
    async def _read_file(self, file_path: Path) -> str:
        """Read file content."""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def _process_attachment(self, attachment: Path, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single attachment.
        
        Args:
            attachment: Path to the attachment
            context: Processing context
            
        Returns:
            Dict containing processed attachment info or None if processing failed
        """
        if attachment in self.processed_attachments:
            return None
        
        try:
            # Create a copy of the attachment in the consolidated directory
            target_dir = Path(context.get('output_dir', '')) / 'attachments'
            target_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = target_dir / attachment.name
            shutil.copy2(attachment, target_path)
            
            # Mark as processed
            self.processed_attachments.add(attachment)
            
            return {
                'original_path': str(attachment),
                'target_path': str(target_path),
                'content': f"[{attachment.name}]({target_path.relative_to(context['output_dir'])})",
                'metadata': {
                    'size': attachment.stat().st_size,
                    'modified': attachment.stat().st_mtime
                }
            }
            
        except Exception as e:
            print(f"Error processing attachment {attachment}: {str(e)}")
            return None 