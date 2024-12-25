"""Reference management utilities for markdown files."""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import re
import logging
from pydantic import BaseModel, Field, ConfigDict

class ReferenceManager(BaseModel):
    """Manages references in markdown files."""
    
    references: Dict[str, str] = Field(default_factory=dict, description="Map of reference IDs to paths")
    image_refs: Dict[str, str] = Field(default_factory=dict, description="Map of image references to paths")
    link_refs: Dict[str, str] = Field(default_factory=dict, description="Map of link references to paths")
    processed_refs: Set[str] = Field(default_factory=set, description="Set of processed reference IDs")
    base_path: Optional[Path] = Field(default=None, description="Base path for resolving relative references")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

    def __init__(self, config: Dict[str, Any]):
        """Initialize the reference manager.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_path = Path(config.get('base_path', '.'))

    def add_reference(self, ref_id: str, path: str) -> None:
        """Add a reference.
        
        Args:
            ref_id: Reference ID
            path: Path to referenced file
        """
        self.references[ref_id] = str(path)

    def add_image_ref(self, ref_id: str, path: str) -> None:
        """Add an image reference.
        
        Args:
            ref_id: Reference ID
            path: Path to image file
        """
        self.image_refs[ref_id] = str(path)

    def add_link_ref(self, ref_id: str, path: str) -> None:
        """Add a link reference.
        
        Args:
            ref_id: Reference ID
            path: Path to linked file
        """
        self.link_refs[ref_id] = str(path)

    def get_reference(self, ref_id: str) -> Optional[str]:
        """Get a reference path.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            Path to referenced file or None if not found
        """
        return self.references.get(ref_id)

    def get_image_ref(self, ref_id: str) -> Optional[str]:
        """Get an image reference path.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            Path to image file or None if not found
        """
        return self.image_refs.get(ref_id)

    def get_link_ref(self, ref_id: str) -> Optional[str]:
        """Get a link reference path.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            Path to linked file or None if not found
        """
        return self.link_refs.get(ref_id)

    def mark_processed(self, ref_id: str) -> None:
        """Mark a reference as processed.
        
        Args:
            ref_id: Reference ID
        """
        self.processed_refs.add(ref_id)

    def is_processed(self, ref_id: str) -> bool:
        """Check if a reference has been processed.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            True if reference has been processed
        """
        return ref_id in self.processed_refs

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the base path.
        
        Args:
            path: Path to resolve
            
        Returns:
            Resolved absolute path
        """
        if self.base_path:
            return self.base_path / path
        return Path(path)

    def extract_references(self, content: str) -> List[str]:
        """Extract references from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of reference IDs
        """
        # Match markdown reference-style links and images
        ref_pattern = r'\[([^\]]+)\]\[([^\]]+)\]|\!\[([^\]]+)\]\[([^\]]+)\]'
        matches = re.finditer(ref_pattern, content)
        refs = []
        
        for match in matches:
            # Link reference
            if match.group(2):
                refs.append(match.group(2))
            # Image reference
            elif match.group(4):
                refs.append(match.group(4))
        
        return refs

    def update_references(self, content: str, new_base: Optional[str] = None) -> str:
        """Update references in content with new paths.
        
        Args:
            content: Content to update
            new_base: Optional new base path for references
            
        Returns:
            Updated content
        """
        if new_base:
            self.base_path = Path(new_base)
        
        # Update image references
        for ref_id, path in self.image_refs.items():
            pattern = f'\\!\\[([^\\]]*)\\]\\[{re.escape(ref_id)}\\]'
            replacement = f'![\\1]({self.resolve_path(path)})'
            content = re.sub(pattern, replacement, content)
        
        # Update link references
        for ref_id, path in self.link_refs.items():
            pattern = f'\\[([^\\]]*)\\]\\[{re.escape(ref_id)}\\]'
            replacement = f'[\\1]({self.resolve_path(path)})'
            content = re.sub(pattern, replacement, content)
        
        return content

    def clear(self) -> None:
        """Clear all references."""
        self.references.clear()
        self.image_refs.clear()
        self.link_refs.clear()
        self.processed_refs.clear() 