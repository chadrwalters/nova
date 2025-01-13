"""Base tool handler implementation."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from nova.server.types import ToolMetadata


class ToolHandler(ABC):
    """Base class for tool handlers."""

    def __init__(self, schema_path: Path) -> None:
        """Initialize tool handler.

        Args:
            schema_path: Path to schema file
        """
        self.schema_path = schema_path
        with open(schema_path) as f:
            self._schema = json.load(f)

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata.

        Returns:
            Tool metadata dictionary
        """
        pass

    @abstractmethod
    def validate_request(self, request: dict[str, Any]) -> None:
        """Validate tool request.

        Args:
            request: Request dictionary

        Raises:
            ResourceError: If request is invalid
        """
        pass

    @abstractmethod
    def validate_response(self, response: dict[str, Any]) -> None:
        """Validate tool response.

        Args:
            response: Response dictionary

        Raises:
            ResourceError: If response is invalid
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
