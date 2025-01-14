"""Note resource handler implementation."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict
import time
from datetime import datetime
import logging

from fastapi import HTTPException
from nova.stubs.docling import Document, DocumentConverter

from nova.server.errors import ResourceError
from nova.server.types import (
    ResourceHandler,
    ResourceType,
    ResourceMetadata,
)

logger = logging.getLogger(__name__)


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
    """Handler for note resources."""

    RESOURCE_ID = "notes"
    VERSION = "1.0.0"
    VALID_OPERATIONS = {"read", "write", "delete"}

    def __init__(self, store: DocumentConverter) -> None:
        """Initialize the handler.

        Args:
            store: Document converter
        """
        self._store = store
        self._notes: list[Document] | None = None
        self._change_callbacks: list[Callable[[], None]] = []

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata.

        Returns:
            Resource metadata
        """
        metadata: ResourceMetadata = {
            "id": self.RESOURCE_ID,
            "type": ResourceType.NOTE,
            "name": "Notes",
            "version": self.VERSION,
            "modified": time.time(),
            "attributes": {
                "total_notes": len(self._notes or []),
                "total_tags": len(
                    {
                        tag
                        for note in (self._notes or [])
                        for tag in note.metadata.get("tags", [])
                    }
                ),
                "has_attachments": any(
                    bool(note.pictures) for note in (self._notes or [])
                ),
                "metadata": {},
            },
        }
        return metadata

    def validate_access(self, note_id: str) -> bool:
        """Validate access to a note.

        Args:
            note_id: Note ID

        Returns:
            True if access is allowed

        Raises:
            HTTPException: If note not found
        """
        try:
            note = self._store.convert_file(Path(note_id))
            if not isinstance(note, Document):
                raise HTTPException(
                    status_code=404, detail=f"Invalid note type: {type(note)}"
                )
            return True
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ResourceError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to validate access: {str(e)}"
            )

    def get_note_metadata(self, note_id: str) -> dict[str, Any]:
        """Get metadata for a note.

        Args:
            note_id: Note ID

        Returns:
            Note metadata

        Raises:
            HTTPException: If note not found
        """
        try:
            note = self._store.convert_file(Path(note_id))
            if not isinstance(note, Document):
                raise HTTPException(
                    status_code=404, detail=f"Invalid note type: {type(note)}"
                )

            return {
                "id": note_id,
                "type": ResourceType.NOTE,
                "name": note.name,
                "version": self.VERSION,
                "created": note.metadata.get("created", datetime.now().isoformat()),
                "modified": note.metadata.get("modified", datetime.now().isoformat()),
                "size": len(note.text),
                "title": note.metadata.get("title", note.name),
                "tags": note.metadata.get("tags", []),
                "metadata": note.metadata,
            }
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ResourceError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get note metadata: {str(e)}"
            )

    def get_note_content(self, note_id: str) -> str:
        """Get content of a note.

        Args:
            note_id: Note ID

        Returns:
            Note content

        Raises:
            HTTPException: If note not found
        """
        try:
            note = self._store.convert_file(Path(note_id))
            if not isinstance(note, Document):
                raise HTTPException(
                    status_code=404, detail=f"Invalid note type: {type(note)}"
                )
            return note.text
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ResourceError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get note content: {str(e)}"
            )

    def list_notes(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List all notes, optionally filtered by tag.

        Args:
            tag: Optional tag to filter notes by

        Returns:
            List of note metadata dictionaries
        """
        # Lazy load notes
        if self._notes is None:
            input_dir = Path(self._store.input_dir)
            self._notes = sorted(
                [self._store.convert_file(path) for path in input_dir.glob("*.md")],
                key=lambda x: x.name,
            )

        notes = []
        if self._notes:  # Check if notes is not None before iterating
            for note in self._notes:
                note_tags = note.metadata.get("tags", [])
                if tag is None or tag in note_tags:
                    notes.append(
                        {
                            "name": note.name,
                            "title": note.metadata.get("title", note.name),
                            "tags": note_tags,
                            "has_attachments": bool(note.pictures),
                            "modified": note.metadata.get(
                                "modified", datetime.now().isoformat()
                            ),
                            "size": len(note.text),
                            "metadata": note.metadata,
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
                logger.error(f"Error in change callback: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._notes = None
        self._change_callbacks.clear()
