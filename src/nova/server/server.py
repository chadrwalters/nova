"""Nova MCP Server implementation."""

import logging
from collections.abc import Sequence
from pathlib import Path

from nova.bear_parser.parser import BearParser
from nova.server.attachments import AttachmentStore
from nova.server.resources import (
    AttachmentHandler,
    NoteHandler,
    ResourceHandler,
    VectorStoreHandler,
)
from nova.server.tools import (
    ExtractTool,
    ListTool,
    RemoveTool,
    SearchTool,
    ToolHandler,
    ToolMetadata,
)
from nova.server.types import (
    MCPError,
    ProtocolError,
    ResourceError,
    ResourceMetadata,
    ServerConfig,
    ServerState,
    ToolError,
)
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class NovaServer:
    """Nova MCP Server implementation."""

    def __init__(self, config: ServerConfig) -> None:
        """Initialize the MCP server.

        Args:
            config: Server configuration

        Raises:
            ProtocolError: If configuration is invalid
        """
        if not config.host:
            raise ProtocolError("Server host not configured")
        if config.port <= 0:
            raise ProtocolError("Server port must be greater than 0")
        if config.max_connections <= 0:
            raise ProtocolError("Maximum connections must be greater than 0")

        self._config = config
        self._state = ServerState.INITIALIZING
        self._resources: dict[str, ResourceHandler] = {}
        self._tools: dict[str, ToolHandler] = {}
        self._logger = logging.getLogger(__name__)

        logger.info("Initializing Nova MCP server")

    @property
    def state(self) -> ServerState:
        """Get current server state."""
        return self._state

    def _start_server(self) -> bool:
        """Internal method to start the server.

        Returns:
            True if server started successfully, False if error occurred
        """
        try:
            self._validate_configuration()
            self._initialize_resources()
            self._initialize_tools()
            return True
        except MCPError as e:
            self._state = ServerState.ERROR
            logger.error("Failed to start Nova MCP server: %s", str(e))
            return False

    def start(self) -> None:
        """Start the MCP server.

        Raises:
            MCPError: If server fails to start
        """
        if self._state == ServerState.ERROR:
            raise MCPError("Cannot start server in ERROR state")

        if not self._start_server():
            raise MCPError("Server failed to start")

        self._state = ServerState.READY
        logger.info("Nova MCP server started successfully")

    def _stop_server(self) -> bool:
        """Internal method to stop the server.

        Returns:
            True if server stopped successfully, False if error occurred
        """
        try:
            self._cleanup_resources()
            self._cleanup_tools()
            return True
        except MCPError as e:
            self._state = ServerState.ERROR
            logger.error("Failed to stop Nova MCP server: %s", str(e))
            return False

    def stop(self) -> None:
        """Stop the MCP server.

        Raises:
            MCPError: If server fails to stop
        """
        if self._state == ServerState.ERROR:
            raise MCPError("Cannot stop server in ERROR state")

        if not self._stop_server():
            raise MCPError("Server failed to stop")

        self._state = ServerState.SHUTDOWN
        logger.info("Nova MCP server stopped successfully")

    def register_resource(self, resource: ResourceHandler) -> None:
        """Register a new resource.

        Args:
            resource: Resource handler to register

        Raises:
            ResourceError: If resource registration fails
        """
        try:
            metadata = resource.get_metadata()
            self._resources[metadata["id"]] = resource
            logger.info("Registered resource: %s", metadata["id"])
        except Exception as e:
            raise ResourceError(f"Failed to register resource: {str(e)}") from e

    def register_tool(self, tool: ToolHandler) -> None:
        """Register a new tool.

        Args:
            tool: Tool handler to register

        Raises:
            ToolError: If tool registration fails
        """
        try:
            metadata = tool.get_metadata()
            tool_id = metadata["id"]
            self._tools[tool_id] = tool
            logger.info("Registered tool: %s", tool_id)
        except Exception as e:
            raise ToolError(f"Failed to register tool: {str(e)}") from e

    def get_resources(self) -> list[ResourceMetadata]:
        """Get all registered resources.

        Returns:
            List of resource metadata
        """
        return [r.get_metadata() for r in self._resources.values()]

    def get_tools(self) -> Sequence[ToolMetadata]:
        """Get list of registered tools.

        Returns:
            List of tool metadata
        """
        return [tool.get_metadata() for tool in self._tools.values()]

    def _validate_configuration(self) -> None:
        """Validate server configuration.

        Raises:
            ProtocolError: If configuration is invalid
        """
        if not self._config.host or len(self._config.host.strip()) == 0:
            raise ProtocolError("Server host not configured")
        if not self._config.port or self._config.port <= 0:
            raise ProtocolError("Server port not configured")
        if not self._config.max_connections or self._config.max_connections < 1:
            raise ProtocolError("Invalid max_connections value")

    def _initialize_resources(self) -> None:
        """Initialize resource handlers.

        Raises:
            ResourceError: If resource initialization fails
        """
        logger.info("Initializing resources")
        try:
            # Initialize vector store handler
            vector_store = self._get_vector_store()
            self.register_resource(VectorStoreHandler(vector_store))

            # Initialize note handler
            note_store = self._get_note_store()
            self.register_resource(NoteHandler(note_store))

            # Initialize attachment handler
            attachment_store = self._get_attachment_store()
            self.register_resource(AttachmentHandler(attachment_store))

            logger.info("Resource initialization complete")
        except Exception as e:
            raise ResourceError(f"Failed to initialize resources: {str(e)}") from e

    def _get_vector_store(self) -> VectorStore:
        """Get vector store instance.

        Returns:
            Initialized vector store instance

        Raises:
            ResourceError: If vector store initialization fails
        """
        try:
            store_dir = Path(".nova/vector_store")
            store_dir.mkdir(parents=True, exist_ok=True)
            return VectorStore(store_dir)
        except Exception as e:
            raise ResourceError(f"Failed to initialize vector store: {str(e)}") from e

    def _get_note_store(self) -> BearParser:
        """Get note store instance.

        Returns:
            Initialized note store instance

        Raises:
            ResourceError: If note store initialization fails
        """
        try:
            notes_dir = Path(".nova/notes")
            notes_dir.mkdir(parents=True, exist_ok=True)
            return BearParser(notes_dir)
        except Exception as e:
            raise ResourceError(f"Failed to initialize note store: {str(e)}") from e

    def _get_attachment_store(self) -> AttachmentStore:
        """Get attachment store instance.

        Returns:
            Initialized attachment store instance

        Raises:
            ResourceError: If attachment store initialization fails
        """
        try:
            store_dir = Path(".nova/attachments")
            store_dir.mkdir(parents=True, exist_ok=True)
            return AttachmentStore(store_dir)
        except Exception as e:
            raise ResourceError(
                f"Failed to initialize attachment store: {str(e)}"
            ) from e

    def _initialize_tools(self) -> None:
        """Initialize tool handlers.

        Raises:
            ToolError: If tool initialization fails
        """
        logger.info("Initializing tools")
        try:
            # Get schema paths
            schema_dir = Path(__file__).parent / "schemas"
            schema_dir.mkdir(parents=True, exist_ok=True)

            # Initialize vector store for search tool
            vector_store = self._get_vector_store()

            # Initialize tools with schemas
            search_tool = SearchTool(schema_dir / "search.json", vector_store)
            list_tool = ListTool(schema_dir / "list.json")
            extract_tool = ExtractTool(schema_dir / "extract.json")
            remove_tool = RemoveTool(schema_dir / "remove.json")

            # Register tools
            self.register_tool(search_tool)
            self.register_tool(list_tool)
            self.register_tool(extract_tool)
            self.register_tool(remove_tool)

            logger.info("Tool initialization complete")
        except Exception as e:
            raise ToolError(f"Failed to initialize tools: {str(e)}") from e

    def _cleanup_resources(self) -> None:
        """Clean up resource handlers.

        Raises:
            ResourceError: If resource cleanup fails
        """
        logger.info("Cleaning up resources")
        try:
            # Clean up vector store
            if "vector-store" in self._resources:
                logger.info("Cleaning up vector store")
                vector_store = self._get_vector_store()
                vector_store.client.reset()  # Reset Chroma client

            # Clean up note store
            if "notes" in self._resources:
                logger.info("Note store is read-only, no cleanup needed")

            # Clean up attachment store
            if "attachments" in self._resources:
                logger.info("Cleaning up attachment store")
                attachment_store = self._get_attachment_store()
                attachment_store.clear()

            # Clear all resource registrations
            self._resources.clear()
            logger.info("Resource cleanup complete")
        except Exception as e:
            raise ResourceError(f"Failed to clean up resources: {str(e)}") from e

    def _cleanup_tools(self) -> None:
        """Clean up tool handlers.

        Raises:
            ToolError: If tool cleanup fails
        """
        logger.info("Cleaning up tools")
        try:
            # Call cleanup on each tool
            for tool_id, tool in self._tools.items():
                logger.info("Cleaning up tool %s", tool_id)
                tool.cleanup()

            # Clear all tool registrations
            self._tools.clear()
            logger.info("Tool cleanup complete")
        except Exception as e:
            raise ToolError(f"Failed to clean up tools: {str(e)}") from e
