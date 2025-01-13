"""Extract tool implementation."""

import json
from pathlib import Path
from typing import Any, TypedDict

from jsonschema.validators import validate

from nova.server.tools.base import ToolHandler
from nova.server.types import ResourceError, ToolMetadata, ToolType


class ExtractRequest(TypedDict):
    """Extract request type."""

    source_id: str
    target_path: str
    filters: dict[str, Any] | None


class ExtractResult(TypedDict):
    """Extract result type."""

    id: str
    path: str
    metadata: dict[str, Any]


class ExtractTool(ToolHandler):
    """Tool for extracting content."""

    def __init__(self, schema_path: Path) -> None:
        """Initialize extract tool.

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
            "id": "extract",
            "type": ToolType.EXTRACT,
            "name": "Extract Tool",
            "version": "0.1.0",
            "parameters": {
                "source_id": {
                    "type": "string",
                    "description": "Source ID to extract from",
                    "required": True,
                },
                "target_path": {
                    "type": "string",
                    "description": "Target path to extract to",
                    "required": True,
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters to apply",
                    "required": False,
                },
            },
            "capabilities": ["extract"],
        }

    def validate_request(self, request: dict[str, Any]) -> None:
        """Validate extract request.

        Args:
            request: Extract request dictionary

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

            # Extract and validate source_id
            source_id = parameters.get("source_id")
            if not source_id or not isinstance(source_id, str):
                raise ValueError("Missing source_id")

            # Extract and validate target_path
            target_path = parameters.get("target_path")
            if not target_path or not isinstance(target_path, str):
                raise ValueError("Missing target_path")

            # Validate filters if present
            filters = parameters.get("filters")
            if filters is not None and not isinstance(filters, dict):
                raise ValueError("Invalid filters")

        except Exception as e:
            raise ResourceError(f"Invalid extract request: {str(e)}")

    def validate_response(self, response: dict[str, Any]) -> None:
        """Validate extract response.

        Args:
            response: Extract response dictionary

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

            # Validate metadata fields
            metadata = response["metadata"]
            required_fields = ["source", "target", "created", "modified"]
            for field in required_fields:
                if field not in metadata:
                    raise ValueError(f"Missing {field} in metadata")

        except Exception as e:
            raise ResourceError(f"Invalid extract response: {str(e)}")

    def extract(self, request: dict[str, Any]) -> dict[str, Any]:
        """Extract text from file."""
        # Validate request
        if "path" not in request:
            raise ResourceError("Path is required")

        path = Path(request["path"])
        if not path.exists():
            raise ResourceError("Path does not exist")
        if not path.is_file():
            raise ResourceError("Path is not a file")

        try:
            # Extract text from file
            text = self._extract_text(path)

            return {
                "path": str(path),
                "text": text,
                "metadata": {
                    "total_chars": len(text)
                }
            }

        except Exception as e:
            raise ResourceError(f"Failed to extract text: {str(e)}")

    def cleanup(self) -> None:
        """Clean up resources."""
        pass  # Nothing to clean up

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute extract operation.

        Args:
            request: Request dictionary with parameters

        Returns:
            Extract result dictionary

        Raises:
            ResourceError: If request is invalid or operation fails
        """
        return self.extract(request)

    def _extract_text(self, path: Path) -> str:
        """Extract text from file.

        Args:
            path: Path to file

        Returns:
            Extracted text

        Raises:
            ResourceError: If text extraction fails
        """
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ResourceError(f"Failed to extract text: {str(e)}")
