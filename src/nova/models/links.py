"""Link metadata models for Nova document processor."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class LinkType(str, Enum):
    """Types of links between documents."""

    OUTGOING = "outgoing"  # Basic outgoing link
    INCOMING = "incoming"  # Basic incoming link
    BIDIRECTIONAL = "bidirectional"  # Two-way link
    SUMMARY_TO_NOTES = "summary_to_notes"  # Summary points to raw notes section
    NOTES_TO_SUMMARY = "notes_to_summary"  # Raw notes points to summary section
    SUMMARY_TO_ATTACHMENT = "summary_to_attachment"  # Summary points to attachment
    NOTES_TO_ATTACHMENT = "notes_to_attachment"  # Raw notes points to attachment
    ATTACHMENT_TO_SUMMARY = (
        "attachment_to_summary"  # Attachment points to summary section
    )
    ATTACHMENT_TO_NOTES = (
        "attachment_to_notes"  # Attachment points to raw notes section
    )


class LinkContext(BaseModel):
    """Context information for a link."""

    # Source information
    source_file: str = Field(description="Source file path")
    source_section: Optional[str] = Field(None, description="Section ID in source file")
    source_line: Optional[int] = Field(None, description="Line number in source file")
    source_context: Optional[str] = Field(
        None, description="Surrounding text in source file"
    )

    # Target information
    target_file: str = Field(description="Target file path")
    target_section: Optional[str] = Field(None, description="Section ID in target file")
    target_line: Optional[int] = Field(None, description="Line number in target file")
    target_context: Optional[str] = Field(
        None, description="Surrounding text in target file"
    )

    # Link information
    link_type: LinkType = Field(
        default=LinkType.OUTGOING, description="Type of link relationship"
    )
    title: Optional[str] = Field(None, description="Link title or text")
    context: Optional[str] = Field(None, description="Link context or description")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the link was created"
    )

    class Config:
        """Model configuration."""

        arbitrary_types_allowed = True
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
        }


class LinkMap(BaseModel):
    """Map of links between documents."""

    # Links by source file
    outgoing_links: Dict[str, List[LinkContext]] = Field(
        default_factory=dict, description="Links from this document to others"
    )

    # Links by target file
    incoming_links: Dict[str, List[LinkContext]] = Field(
        default_factory=dict, description="Links from other documents to this one"
    )

    def add_link(self, link: LinkContext) -> None:
        """Add a link to the map.

        Args:
            link: Link context to add
        """
        # Add to outgoing links
        if link.source_file not in self.outgoing_links:
            self.outgoing_links[link.source_file] = []
        self.outgoing_links[link.source_file].append(link)

        # Add to incoming links
        if link.target_file not in self.incoming_links:
            self.incoming_links[link.target_file] = []
        self.incoming_links[link.target_file].append(link)

    def get_outgoing_links(self, source_file: str) -> List[LinkContext]:
        """Get all links from a source file.

        Args:
            source_file: Source file path

        Returns:
            List of link contexts
        """
        return self.outgoing_links.get(source_file, [])

    def get_incoming_links(self, target_file: str) -> List[LinkContext]:
        """Get all links to a target file.

        Args:
            target_file: Target file path

        Returns:
            List of link contexts
        """
        return self.incoming_links.get(target_file, [])

    def get_links_by_type(self, link_type: LinkType) -> List[LinkContext]:
        """Get all links of a specific type.

        Args:
            link_type: Type of links to get

        Returns:
            List of link contexts
        """
        links = []
        for source_links in self.outgoing_links.values():
            links.extend([link for link in source_links if link.link_type == link_type])
        return links

    def validate_links(self) -> List[str]:
        """Validate all links in the map.

        Returns:
            List of validation error messages
        """
        errors = []

        # Check for circular references
        visited = set()
        for source_file in self.outgoing_links:
            if source_file not in visited:
                path = []
                if self._has_circular_reference(source_file, path, visited):
                    errors.append(f"Circular reference detected: {' -> '.join(path)}")

        # Check for broken links (files that don't exist)
        all_files = set(self.outgoing_links.keys()) | set(self.incoming_links.keys())
        for file_path in all_files:
            if not Path(file_path).exists():
                errors.append(f"Broken link: File does not exist: {file_path}")

        return errors

    def _has_circular_reference(
        self, current: str, path: List[str], visited: set
    ) -> bool:
        """Check for circular references starting from a file.

        Args:
            current: Current file being checked
            path: Current path being explored
            visited: Set of already visited files

        Returns:
            True if a circular reference is found, False otherwise
        """
        if current in path:
            path.append(current)
            return True

        path.append(current)
        visited.add(current)

        for link in self.get_outgoing_links(current):
            if self._has_circular_reference(link.target_file, path.copy(), visited):
                return True

        return False
