"""List tool implementation."""

import json
from pathlib import Path
from typing import Any, TypedDict

from jsonschema.validators import validate

from nova.server.tools.base import ToolHandler
from nova.server.types import ResourceError, ToolMetadata, ToolType


class ListRequest(TypedDict):
    """List request type."""

    path: str
    recursive: bool | None
    filters: dict[str, Any] | None


class ListResult(TypedDict):
    """List result type."""

    path: str
    entries: list[dict[str, Any]]
    metadata: dict[str, Any]


class ListTool(ToolHandler):
    """Tool for listing directory contents."""

    def __init__(self, schema_path: Path) -> None:
        """Initialize list tool.

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
            "id": "list",
            "type": ToolType.LIST,
            "name": "List Tool",
            "version": "0.1.0",
            "parameters": {
                "path": {
                    "type": "string",
                    "description": "Path to list contents of",
                    "required": True,
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively",
                    "required": False,
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters to apply",
                    "required": False,
                },
            },
            "capabilities": ["list"],
        }

    def validate_request(self, request: dict[str, Any]) -> None:
        """Validate list request.

        Args:
            request: List request dictionary

        Raises:
            ResourceError: If request is invalid
        """
        try:
            # Extract path from parameters
            parameters = request.get("parameters", {})
            if "path" not in parameters:
                # Try to get path from root level for backward compatibility
                if "path" in request:
                    parameters["path"] = request["path"]
                    request["parameters"] = parameters
                else:
                    raise ValueError("'path' is a required property")
            path = parameters["path"]
            if not isinstance(path, str):
                raise ValueError("Path must be a string")

            # Get recursive flag
            recursive = parameters.get("recursive")
            if recursive is not None and not isinstance(recursive, bool):
                raise ResourceError("Invalid list request: recursive must be a boolean")

            # Get filters
            filters = parameters.get("filters")
            if filters is not None and not isinstance(filters, dict):
                raise ValueError("Invalid filters")

            # Validate against schema
            validate(instance=request, schema=self._schema)

        except ValueError as e:
            raise ResourceError(f"Invalid list request: {str(e)}")

    def validate_response(self, response: dict[str, Any]) -> None:
        """Validate list response.

        Args:
            response: List response dictionary

        Raises:
            ResourceError: If response is invalid
        """
        try:
            # Validate against schema
            validate(instance={"response": response}, schema=self._schema)

        except Exception as e:
            raise ResourceError(f"Invalid list response: {str(e)}")

    def execute(self, request: dict[str, Any]) -> ListResult:
        """Execute list operation.

        Args:
            request: Request dictionary with parameters

        Returns:
            List result dictionary

        Raises:
            ResourceError: If request is invalid or operation fails
        """
        # Validate request
        self.validate_request(request)

        # Get parameters
        params = request.get("parameters", {})
        path = params.get("path")
        if not path:
            raise ResourceError("Path parameter is required")

        recursive = params.get("recursive", False)
        filters = params.get("filters", {})

        try:
            target_path = Path(path)
            if not target_path.exists():
                raise ResourceError(f"Path does not exist: {path}")

            if not target_path.is_dir():
                raise ResourceError("Path is not a directory")

            entries = []
            if recursive:
                for entry in target_path.rglob("*"):
                    if self._should_include(entry, filters):
                        entries.append(self._get_entry_info(entry))
            else:
                for entry in target_path.iterdir():
                    if self._should_include(entry, filters):
                        entries.append(self._get_entry_info(entry))

            return {
                "path": str(target_path),
                "entries": entries,
                "metadata": {
                    "total": len(entries),
                    "recursive": recursive,
                    "filters": filters,
                },
            }
        except NotADirectoryError:
            raise ResourceError("Path is not a directory")
        except Exception as e:
            raise ResourceError(f"Failed to list entries: {str(e)}")

    def _get_entry_info(self, path: Path) -> dict[str, Any]:
        """Get entry info."""
        return {
            "name": path.name,
            "path": str(path),
            "type": "file" if path.is_file() else "dir",
            "size": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }

    def _should_include(self, entry: Path, filters: dict[str, Any]) -> bool:
        """Check if entry should be included based on filters."""
        if "type" in filters:
            if filters["type"] == "file" and not entry.is_file():
                return False
            if filters["type"] == "dir" and not entry.is_dir():
                return False

        if "name" in filters:
            # Remove extension for name comparison
            entry_name = entry.name
            if "." in entry_name:
                entry_name = entry_name.rsplit(".", 1)[0]
            if filters["name"] != entry_name:
                return False

        if "extension" in filters:
            if not entry.is_file():  # Only apply extension filter to files
                return False
            if not entry.name.endswith(filters["extension"]):
                return False

        return True

    def cleanup(self) -> None:
        """Clean up resources."""
        pass  # Nothing to clean up

    def list(self, request: dict[str, Any]) -> dict[str, Any]:
        """List directory contents."""
        # Validate request
        if "path" not in request:
            raise ResourceError("Path is required")

        path = Path(request["path"])
        if not path.exists():
            raise ResourceError("Path does not exist")
        if not path.is_dir():
            raise ResourceError("Path is not a directory")

        recursive = request.get("recursive", False)
        if not isinstance(recursive, bool):
            raise ResourceError("Recursive must be a boolean")

        filters = request.get("filters", {})
        if not isinstance(filters, dict):
            raise ResourceError("Filters must be an object")

        try:
            entries = []
            if recursive:
                for entry_path in path.rglob("*"):
                    if self._should_include(entry_path, filters):
                        entries.append(self._get_entry_info(entry_path))
            else:
                for entry_path in path.iterdir():
                    if self._should_include(entry_path, filters):
                        entries.append(self._get_entry_info(entry_path))

            return {
                "path": str(path),
                "entries": entries,
                "metadata": {"total": len(entries), "recursive": recursive},
            }

        except Exception as e:
            raise ResourceError(f"Failed to list entries: {str(e)}")
