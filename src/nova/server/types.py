"""Type definitions for the Nova MCP server module."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Protocol, TypedDict
from collections.abc import Callable


class ServerState(Enum):
    """Server state enumeration."""

    INITIALIZING = auto()
    READY = auto()
    ERROR = auto()
    SHUTDOWN = auto()


class ResourceType(Enum):
    """Resource type enumeration."""

    VECTOR_STORE = auto()
    NOTE = auto()
    ATTACHMENT = auto()


class ToolType(Enum):
    """Tool type enumeration."""

    SEARCH = auto()
    LIST = auto()
    EXTRACT = auto()
    REMOVE = auto()


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class ProtocolError(MCPError):
    """Raised for protocol-level errors."""

    pass


class ResourceError(MCPError):
    """Raised for resource-related errors."""

    pass


class ToolError(MCPError):
    """Raised for tool-related errors."""

    pass


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str
    port: int
    input_dir: str | None = None
    store_dir: str | None = None
    debug: bool = False
    max_connections: int = 10


class ResourceMetadata(TypedDict):
    """Resource metadata type."""

    id: str
    type: ResourceType
    name: str
    version: str
    modified: float
    attributes: dict[str, Any]


class ToolMetadata(TypedDict):
    """Tool metadata type."""

    id: str
    type: ToolType
    name: str
    version: str
    parameters: dict[str, Any]
    capabilities: list[str]


class ResourceHandler(Protocol):
    """Protocol for resource handlers."""

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata.

        Returns:
            Dictionary containing resource metadata
        """
        ...

    def cleanup(self) -> None:
        """Clean up resources."""
        ...

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation.

        Args:
            operation: Operation to validate

        Returns:
            True if operation is allowed
        """
        ...

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback.

        Args:
            callback: Function to call when resource changes
        """
        ...


class PromptTemplate(TypedDict):
    """Prompt template type."""

    id: str
    name: str
    version: str
    template: str
    variables: dict[str, str]
    description: str | None


class PromptContext(TypedDict):
    """Prompt context type."""

    template_id: str
    variables: dict[str, Any]
    system_instructions: list[str]
    metadata: dict[str, Any]


class PromptError(MCPError):
    """Raised for prompt-related errors."""

    pass


class PromptManager(Protocol):
    """Protocol for prompt management."""

    def get_template(self, template_id: str) -> PromptTemplate:
        """Get prompt template by ID."""
        ...

    def validate_template(self, template: PromptTemplate) -> bool:
        """Validate prompt template."""
        ...

    def assemble_context(self, context: PromptContext) -> str:
        """Assemble prompt context into final prompt."""
        ...

    def on_template_change(self, callback: Callable[[str], None]) -> None:
        """Register template change callback."""
        ...


class ErrorCode(Enum):
    """Error codes for Nova server."""

    # General errors
    UNKNOWN_ERROR = (
        1000,
        "Unknown error occurred",
        "An unknown error occurred. Please try again or contact support if the issue persists.",
    )
    INVALID_REQUEST = (
        1001,
        "Invalid request",
        "Please check your request format and try again.",
    )
    UNAUTHORIZED = (
        1002,
        "Unauthorized",
        "Please verify your credentials and try again.",
    )
    RATE_LIMITED = (1003, "Rate limited", "Please wait and try again later.")

    # Resource errors
    RESOURCE_NOT_FOUND = (
        2000,
        "Resource not found",
        "Please verify the resource exists and try again.",
    )
    RESOURCE_ALREADY_EXISTS = (
        2001,
        "Resource already exists",
        "Please try a different name or ID.",
    )
    RESOURCE_ACCESS_DENIED = (
        2002,
        "Resource access denied",
        "Please check your permissions and try again.",
    )
