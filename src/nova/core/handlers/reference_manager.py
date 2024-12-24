"""Reference manager for handling cross-references and anchor IDs."""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from nova.core.config import ProcessorConfig

class ReferenceManager:
    """Manages cross-references and anchor IDs for markdown files."""

    def __init__(self, nova_config: ProcessorConfig):
        """Initialize the reference manager.

        Args:
            nova_config: Nova configuration object
        """
        self._anchor_ids = {}  # Map of file to anchor ID
        self._references = {}  # Map of source file to set of referenced files
        self._reverse_refs = {}  # Map of referenced file to set of source files
        self.nova_config = nova_config

    def generate_anchor_id(self, filename: str, content: Optional[str] = None) -> str:
        """Generate a unique anchor ID for a file.

        Args:
            filename: Name of the file
            content: Optional content to include in hash

        Returns:
            Unique anchor ID
        """
        # Create hash input
        hash_input = filename
        if content:
            hash_input += content

        # Generate MD5 hash
        hash_obj = hashlib.md5(hash_input.encode())
        anchor_id = hash_obj.hexdigest()[:8]

        # Store anchor ID
        self._anchor_ids[filename] = anchor_id

        return anchor_id

    def add_reference(self, source_file: str, referenced_file: str):
        """Add a reference between files.

        Args:
            source_file: File containing the reference
            referenced_file: File being referenced
        """
        # Add forward reference
        if source_file not in self._references:
            self._references[source_file] = set()
        self._references[source_file].add(referenced_file)

        # Add reverse reference
        if referenced_file not in self._reverse_refs:
            self._reverse_refs[referenced_file] = set()
        self._reverse_refs[referenced_file].add(source_file)

    def get_anchor_id(self, filename: str) -> Optional[str]:
        """Get anchor ID for a file.

        Args:
            filename: Name of the file

        Returns:
            Anchor ID if found, None otherwise
        """
        return self._anchor_ids.get(filename)

    def get_references(self, source_file: str) -> Set[str]:
        """Get files referenced by a source file.

        Args:
            source_file: Source file to check

        Returns:
            Set of referenced files
        """
        return self._references.get(source_file, set())

    def get_reverse_references(self, referenced_file: str) -> Set[str]:
        """Get files that reference a file.

        Args:
            referenced_file: Referenced file to check

        Returns:
            Set of source files
        """
        return self._reverse_refs.get(referenced_file, set())

    def update_references(self, content: str, source_file: str) -> str:
        """Update references in content with anchor IDs.

        Args:
            content: Content to update
            source_file: Source file containing the content

        Returns:
            Updated content
        """
        # Find attachment references
        pattern = r'--==ATTACHMENT_BLOCK:\s*([^=\s]+)\s*==--'
        matches = re.finditer(pattern, content)

        # Update each reference
        for match in matches:
            filename = match.group(1)
            anchor_id = self.get_anchor_id(filename)
            if anchor_id:
                # Add reference
                self.add_reference(source_file, filename)
                # Update link
                link = f'[{filename}](attachments.md#{anchor_id})'
                content = content.replace(match.group(0), link)

        return content

    def add_navigation_links(self, content: str, source_file: str) -> str:
        """Add navigation links for cross-references.

        Args:
            content: Content to update
            source_file: Source file containing the content

        Returns:
            Updated content with navigation links
        """
        # Get referenced files
        referenced = self.get_references(source_file)
        if not referenced:
            return content

        # Add navigation section
        nav_links = []
        nav_links.append("\n## Referenced Files\n")
        for ref in sorted(referenced):
            anchor_id = self.get_anchor_id(ref)
            if anchor_id:
                nav_links.append(f"- [{ref}](attachments.md#{anchor_id})")

        return content + "\n".join(nav_links)

    def validate_references(self) -> List[str]:
        """Validate all references.

        Returns:
            List of error messages, empty if no errors
        """
        errors = []
        visited = set()
        path = []

        def check_circular(source: str) -> None:
            if source in path:
                cycle = ' -> '.join(path[path.index(source):] + [source])
                errors.append(f"Circular reference detected: {cycle}")
                return
            
            if source in visited:
                return

            visited.add(source)
            path.append(source)
            
            for target in self.get_references(source):
                check_circular(target)
            
            path.pop()

        # Check for missing anchor IDs
        for source, targets in self._references.items():
            for target in targets:
                if target not in self._anchor_ids:
                    errors.append(f"Missing anchor ID for {target} referenced in {source}")

        # Check for circular references
        for source in self._references:
            if source not in visited:
                check_circular(source)

        return errors