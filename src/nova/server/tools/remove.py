"""Remove tool implementation."""

import json
import time
from pathlib import Path
from typing import Any, TypedDict

from jsonschema.validators import validate

from nova.server.tools.base import ToolHandler
from nova.server.types import ResourceError, ToolMetadata, ToolType


class RemoveRequest(TypedDict):
    """Remove request type."""

    target_id: str
    force: bool | None


class RemoveResult(TypedDict):
    """Remove result type."""

    id: str
    success: bool
    metadata: dict[str, Any]


class RemoveTool(ToolHandler):
    """Tool for removing content."""

    def __init__(self, schema_path: Path) -> None:
        """Initialize remove tool.

        Args:
            schema_path: Path to schema file
        """
        super().__init__(schema_path)

        # Load schema
        with open(schema_path) as f:
            self._schema = json.load(f)

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata.

        Returns:
            Tool metadata dictionary
        """
        return {
            "id": "remove",
            "type": ToolType.REMOVE,
            "name": "Remove Tool",
            "version": "0.1.0",
            "parameters": {
                "target_id": {
                    "type": "string",
                    "description": "ID of target to remove",
                    "required": True,
                },
                "force": {
                    "type": "boolean",
                    "description": "Whether to force removal",
                    "required": False,
                },
            },
            "capabilities": ["remove"],
        }

    def validate_request(self, request: dict[str, Any]) -> None:
        """Validate remove request.

        Args:
            request: Remove request dictionary

        Raises:
            ResourceError: If request is invalid
        """
        try:
            # Validate against schema
            validate(instance=request, schema=self._schema)

            # Extract parameters from request
            parameters = request.get("parameters", {})
            if not isinstance(parameters, dict):
                raise ValueError("Invalid parameters")

            # Extract and validate target_id
            target_id = parameters.get("target_id")
            if not target_id or not isinstance(target_id, str):
                raise ValueError("Missing target_id")

            # Validate force flag if present
            force = parameters.get("force")
            if force is not None and not isinstance(force, bool):
                raise ValueError("Invalid force flag")

            # Validate filters if present
            filters = parameters.get("filters")
            if filters is not None and not isinstance(filters, dict):
                raise ValueError("Invalid filters")

        except Exception as e:
            raise ResourceError(f"Invalid remove request: {str(e)}")

    def validate_response(self, response: dict[str, Any]) -> None:
        """Validate remove response.

        Args:
            response: Remove response dictionary

        Raises:
            ResourceError: If response is invalid
        """
        try:
            # Check required fields
            if "id" not in response:
                raise ValueError("Missing id")
            if "success" not in response:
                raise ValueError("Missing success")
            if "metadata" not in response:
                raise ValueError("Missing metadata")

            # Validate types
            if not isinstance(response["id"], str):
                raise ValueError("Invalid id type")
            if not isinstance(response["success"], bool):
                raise ValueError("Invalid success type")
            if not isinstance(response["metadata"], dict):
                raise ValueError("Invalid metadata type")

        except Exception as e:
            raise ResourceError(f"Invalid remove response: {str(e)}")

    def remove(self, request: dict[str, Any]) -> dict[str, Any]:
        """Remove file."""
        # Validate request
        self.validate_request(request)

        # Extract parameters
        params = request.get("parameters", {})
        target_id = params.get("target_id")
        # Note: force parameter is reserved for future use
        _ = params.get("force", False)

        if not target_id:
            raise ResourceError("target_id is required")

        try:
            # For now, just return success since we don't have actual file removal
            return {
                "id": request.get("id", "remove-1"),
                "success": True,
                "metadata": {"removed_at": time.time()},
            }

        except Exception as e:
            raise ResourceError(f"Failed to remove file: {str(e)}")

    def cleanup(self) -> None:
        """Clean up resources."""
        pass  # Nothing to clean up
