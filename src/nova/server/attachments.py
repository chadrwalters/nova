"""Attachment store implementation."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from nova.server.types import ResourceError


class AttachmentStore:
    """Store for managing attachments."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize store.

        Args:
            storage_path: Path to store attachments
        """
        self.storage_path = storage_path
        self.mime_types = {"image/png", "image/jpeg", "application/pdf", "image/tiff"}
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ResourceError(f"Failed to create storage directory: {str(e)}")

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Add an attachment.

        Args:
            file_path: Path to file to attach
            metadata: Metadata for attachment

        Returns:
            Attachment info dictionary or None if failed
        """
        try:
            # Generate unique ID
            attachment_id = str(int(datetime.now().timestamp() * 1000))
            target_path = self.storage_path / attachment_id

            # Copy file
            shutil.copy2(file_path, target_path)

            # Create info
            info = {
                "id": attachment_id,
                "name": file_path.name,
                "mime_type": metadata.get("mime_type", "application/octet-stream"),
                "size": file_path.stat().st_size,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat(),
                "metadata": metadata,
            }

            # Save info
            info_path = target_path.with_suffix(".json")
            with info_path.open("w") as f:
                json.dump(info, f)

            return info

        except Exception as e:
            raise ResourceError(f"Failed to add attachment: {str(e)}")

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any] | None:
        """Get attachment information.

        Args:
            attachment_id: Unique identifier for attachment

        Returns:
            Attachment info dictionary or None if not found
        """
        try:
            info_path = self.storage_path / f"{attachment_id}.json"
            if not info_path.exists():
                return None

            with info_path.open() as f:
                info: dict[str, Any] = json.load(f)
                return info

        except Exception as e:
            raise ResourceError(f"Failed to get attachment info: {str(e)}")

    def update_attachment_metadata(
        self, attachment_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update attachment metadata.

        Args:
            attachment_id: Unique identifier for attachment
            metadata: New metadata for attachment

        Returns:
            Updated attachment info dictionary or None if not found
        """
        try:
            info_path = self.storage_path / f"{attachment_id}.json"
            if not info_path.exists():
                return None

            with info_path.open() as f:
                info: dict[str, Any] = json.load(f)

            info["metadata"] = metadata
            info["modified"] = datetime.now().isoformat()

            with info_path.open("w") as f:
                json.dump(info, f)

            return info

        except Exception as e:
            raise ResourceError(f"Failed to update attachment metadata: {str(e)}")

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment.

        Args:
            attachment_id: Unique identifier for attachment

        Returns:
            True if deleted, False if not found
        """
        try:
            file_path = self.storage_path / attachment_id
            info_path = file_path.with_suffix(".json")

            if not file_path.exists() or not info_path.exists():
                return False

            file_path.unlink()
            info_path.unlink()
            return True

        except Exception as e:
            raise ResourceError(f"Failed to delete attachment: {str(e)}")

    def list_attachments(self) -> list[dict[str, Any]]:
        """List all attachments.

        Returns:
            List of attachment info dictionaries
        """
        try:
            attachments = []
            for info_path in self.storage_path.glob("*.json"):
                with info_path.open() as f:
                    attachments.append(json.load(f))
            return attachments

        except Exception as e:
            raise ResourceError(f"Failed to list attachments: {str(e)}")

    def count_attachments(self) -> int:
        """Count total attachments.

        Returns:
            Number of attachments
        """
        try:
            return len(list(self.storage_path.glob("*.json")))
        except Exception as e:
            raise ResourceError(f"Failed to count attachments: {str(e)}")

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.storage_path.exists():
                shutil.rmtree(self.storage_path)
        except Exception as e:
            raise ResourceError(f"Failed to clean up: {str(e)}")
