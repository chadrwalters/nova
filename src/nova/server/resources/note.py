"""Note resource handler implementation."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from nova.bear_parser.parser import BearNote, BearParser
from nova.server.types import (
    ResourceError,
    ResourceHandler,
    ResourceMetadata,
)


class NoteAttributes(TypedDict):
    """Note attributes type."""

    title: str
    created_at: float
    updated_at: float
    tags: list[str]
    has_attachments: bool
    total_notes: int
    total_tags: int
    metadata: dict[str, Any]


class NoteMetadata(TypedDict):
    """Note metadata type."""

    id: str
    type: str
    name: str
    version: str
    modified: float
    attributes: NoteAttributes


class NoteHandler(ResourceHandler):
    """Handler for note operations."""

    VERSION = "1.0.0"
    RESOURCE_ID = "notes"  # Fixed ID
    SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "note_resource.json"

    def __init__(self, note_store: BearParser) -> None:
        """Initialize note handler.

        Args:
            note_store: Note store instance to manage notes
        """
        self._store = note_store
        self._notes: list[BearNote] | None = None
        self._tags: set[str] = set()
        self._change_callbacks: list[Callable[[], None]] = []

        # Load schema
        with open(self.SCHEMA_PATH) as f:
            self._schema = json.load(f)

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata.

        Returns:
            Resource metadata
        """
        return ResourceMetadata(
            id=self.id,
            type="note",
            name=self.name,
            created=self.created,
            modified=self.modified,
            size=self.size,
            metadata=self.metadata,
        )

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation.

        Args:
            operation: Operation to validate

        Returns:
            bool: True if operation is allowed
        """
        valid_ops = {"read", "write", "delete"}
        return operation in valid_ops

    def get_note_metadata(self, note_id: str) -> dict[str, Any]:
        """Get metadata for a specific note.

        Args:
            note_id: ID of the note to get metadata for

        Returns:
            Dictionary containing note metadata

        Raises:
            ResourceError: If note is not found
        """
        # Lazy load notes
        if self._notes is None:
            self._notes = self._store.parse_directory()

        # Find note by ID (using title as ID for now)
        for note in self._notes:
            if note.title == note_id:
                return {
                    "id": note.title,
                    "title": note.title,
                    "tags": note.tags,
                    "has_attachments": bool(note.attachments),
                    "metadata": note.metadata,
                    "content_length": len(note.content),
                }

        raise ResourceError(f"Note not found: {note_id}")

    def get_note_content(
        self, note_id: str, start: int | None = None, end: int | None = None
    ) -> str:
        """Get content for a specific note.

        Args:
            note_id: ID of the note to get content for
            start: Optional start position for content streaming
            end: Optional end position for content streaming

        Returns:
            Note content (full or partial based on start/end)

        Raises:
            ResourceError: If note is not found or content range is invalid
        """
        try:
            content = str(self._store.read(note_id))  # Convert to str
            if start is not None and end is not None:
                if start < 0 or end < start or end > len(content):
                    raise ValueError("Invalid content range")
                return content[start:end]
            return content
        except (FileNotFoundError, ValueError) as e:
            raise ResourceError(f"Failed to get note content: {str(e)}")

    def list_notes(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List all notes, optionally filtered by tag.

        Args:
            tag: Optional tag to filter notes by

        Returns:
            List of note metadata dictionaries
        """
        # Lazy load notes
        if self._notes is None:
            self._notes = self._store.parse_directory()

        notes = []
        for note in self._notes:
            if tag is None or tag in note.tags:
                notes.append(
                    {
                        "id": note.title,
                        "title": note.title,
                        "tags": note.tags,
                        "has_attachments": bool(note.attachments),
                        "metadata": note.metadata,
                        "content_length": len(note.content),
                    }
                )
        return notes

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback.

        Args:
            callback: Function to call when resource changes
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify registered callbacks of change."""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                # Log error but continue notifying other callbacks
                print(f"Error in change callback: {str(e)}")
