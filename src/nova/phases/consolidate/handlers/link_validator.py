"""Handler for validating and updating links during consolidation."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import aiofiles
import aiohttp

from nova.phases.core.base_handler import BaseHandler

class LinkValidatorHandler(BaseHandler):
    """Handles validation and updating of links during consolidation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the link validator.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.config = config or {}
        
        # Initialize link tracking
        self.validated_links: Set[str] = set()
        self.broken_links: Set[str] = set()
        
        # Configure link handling
        self.handle_missing = self.config.get('handle_missing', {
            'action': 'warn'  # Options: warn, error, ignore
        })
        self.create_relative_paths = self.config.get('create_relative_paths', True)
    
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file contains links that need validation.
        
        Args:
            file_path: Path to the markdown file
            attachments: Optional list of attachments
            
        Returns:
            bool: True if file has markdown extension
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}
    
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process and validate links in the markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments
            
        Returns:
            Dict containing:
                - content: Updated markdown content
                - metadata: Link validation metadata
                - processed_attachments: Empty list
                - errors: List of validation errors
        """
        result = {
            'content': '',
            'metadata': {
                'links': {
                    'valid': [],
                    'broken': [],
                    'updated': []
                }
            },
            'processed_attachments': [],
            'errors': []
        }
        
        try:
            # Read content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Extract and validate links
            links = self._extract_links(content)
            
            # Process each link
            for link_text, link_url in links:
                try:
                    validated_url = await self._validate_link(
                        link_url, 
                        file_path, 
                        attachments or [],
                        context
                    )
                    
                    if validated_url:
                        # Update link in content if URL changed
                        if validated_url != link_url:
                            old_link = f"[{link_text}]({link_url})"
                            new_link = f"[{link_text}]({validated_url})"
                            content = content.replace(old_link, new_link)
                            result['metadata']['links']['updated'].append({
                                'old': link_url,
                                'new': validated_url
                            })
                        result['metadata']['links']['valid'].append(validated_url)
                    else:
                        result['metadata']['links']['broken'].append(link_url)
                        
                        # Handle broken links according to config
                        if self.handle_missing['action'] == 'warn':
                            result['errors'].append(f"Warning: Broken link {link_url}")
                        elif self.handle_missing['action'] == 'error':
                            raise ValueError(f"Broken link found: {link_url}")
                        # For 'ignore', we do nothing
                
                except Exception as e:
                    result['errors'].append(f"Error processing link {link_url}: {str(e)}")
            
            result['content'] = content
            
        except Exception as e:
            result['errors'].append(f"Error validating links in {file_path}: {str(e)}")
        
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
            isinstance(result['errors'], list) and
            'links' in result['metadata']
        )
    
    def _extract_links(self, content: str) -> List[Tuple[str, str]]:
        """Extract all links from markdown content.
        
        Returns list of (link_text, link_url) tuples.
        """
        links = []
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            links.append((match.group(1), match.group(2)))
        return links
    
    async def _validate_link(
        self, 
        link_url: str, 
        source_file: Path,
        attachments: List[Path],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Validate and potentially update a link.
        
        Returns:
            Updated URL if valid, None if invalid
        """
        # Skip if already validated
        if link_url in self.validated_links:
            return link_url
        if link_url in self.broken_links:
            return None
        
        try:
            # Handle different link types
            if link_url.startswith(('http://', 'https://')):
                # External link
                if await self._validate_external_link(link_url):
                    self.validated_links.add(link_url)
                    return link_url
                self.broken_links.add(link_url)
                return None
                
            else:
                # Local link
                return await self._validate_local_link(
                    link_url,
                    source_file,
                    attachments,
                    context
                )
                
        except Exception as e:
            print(f"Error validating link {link_url}: {str(e)}")
            return None
    
    async def _validate_external_link(self, url: str) -> bool:
        """Validate an external URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as response:
                    return response.status == 200
        except:
            return False
    
    async def _validate_local_link(
        self,
        link_url: str,
        source_file: Path,
        attachments: List[Path],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Validate and update a local link."""
        try:
            # Convert to Path for easier manipulation
            link_path = Path(link_url)
            
            # Check if it points to an attachment
            for attachment in attachments:
                if attachment.name == link_path.name:
                    # Update to point to new location
                    new_path = (
                        Path(context.get('output_dir', '.')) / 
                        'attachments' / 
                        attachment.name
                    )
                    return str(new_path.relative_to(context.get('output_dir', '.')))
            
            # Check if it's a relative link to another markdown file
            target_path = source_file.parent / link_path
            if target_path.exists():
                if self.create_relative_paths:
                    return str(target_path.relative_to(context.get('output_dir', '.')))
                return link_url
            
            return None
            
        except Exception as e:
            print(f"Error validating local link {link_url}: {str(e)}")
            return None 