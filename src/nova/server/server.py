"""Nova MCP Server implementation."""

import logging
from pathlib import Path
from typing import cast
from threading import Lock

from nova.stubs.docling import DocumentConverter, InputFormat

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
)
from nova.server.types import (
    MCPError,
    ServerState,
    ResourceMetadata,
    ToolMetadata,
    ServerConfig,
    ProtocolError,
    ResourceError,
    ToolError,
)
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class NovaServer:
    """Nova MCP Server implementation."""

    def __init__(self, config: ServerConfig) -> None:
        """Initialize server.

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
        self._resources: dict[str, ResourceHandler] = {}
        self._tools: dict[str, ToolHandler] = {}
        self._state = ServerState.INITIALIZING
        self._lock = Lock()

        # Initialize stores as None
        self._note_store: DocumentConverter | None = None
        self._attachment_store: AttachmentStore | None = None
        self._vector_store: VectorStore | None = None

        # Track initialization
        self._resources_initialized = False
        self._tools_initialized = False

    @property
    def state(self) -> ServerState:
        """Get server state."""
        return self._state

    def _get_note_store(self) -> DocumentConverter:
        """Get note store instance.

        Returns:
            Note store instance

        Raises:
            ProtocolError: If store initialization fails
        """
        if self._note_store is None:
            input_dir = self._config.input_dir or str(Path.home() / ".nova" / "input")
            logger.info(
                "Initializing document converter with input directory: %s", input_dir
            )
            self._note_store = DocumentConverter(allowed_formats=[InputFormat.MD])
        return self._note_store

    def _get_attachment_store(self) -> AttachmentStore:
        """Get attachment store instance.

        Returns:
            Attachment store instance

        Raises:
            ProtocolError: If store initialization fails
        """
        if self._attachment_store is None:
            store_dir = self._config.store_dir or str(Path.home() / ".nova" / "store")
            logger.info("Initializing attachment store with directory: %s", store_dir)
            self._attachment_store = AttachmentStore(Path(store_dir) / "attachments")
        return self._attachment_store

    def _get_vector_store(self) -> VectorStore:
        """Get vector store instance.

        Returns:
            Vector store instance

        Raises:
            ProtocolError: If store initialization fails
        """
        if self._vector_store is None:
            store_dir = self._config.store_dir or str(Path.home() / ".nova" / "store")
            logger.info("Initializing vector store with directory: %s", store_dir)
            self._vector_store = VectorStore(Path(store_dir) / "vectors")
        return self._vector_store

    def _ensure_resource(self, resource_id: str) -> None:
        """Ensure a specific resource is initialized.

        Args:
            resource_id: ID of resource to initialize

        Raises:
            ResourceError: If resource initialization fails
        """
        if resource_id not in self._resources:
            with self._lock:
                if resource_id not in self._resources:
                    try:
                        logger.info("Initializing resource: %s", resource_id)
                        handler: ResourceHandler
                        if resource_id == "notes":
                            handler = cast(
                                ResourceHandler, NoteHandler(self._get_note_store())
                            )
                        elif resource_id == "attachments":
                            handler = cast(
                                ResourceHandler,
                                AttachmentHandler(self._get_attachment_store()),
                            )
                        elif resource_id == "vectors":
                            handler = cast(
                                ResourceHandler,
                                VectorStoreHandler(self._get_vector_store()),
                            )
                        else:
                            raise ResourceError(f"Unknown resource ID: {resource_id}")

                        self.register_resource(handler)
                        logger.info(
                            "Resource initialized successfully: %s", resource_id
                        )
                    except Exception as e:
                        self._state = ServerState.ERROR
                        raise ResourceError(
                            f"Failed to initialize resource {resource_id}: {str(e)}"
                        ) from e

    def _ensure_tool(self, tool_id: str) -> None:
        """Ensure a specific tool is initialized.

        Args:
            tool_id: ID of tool to initialize

        Raises:
            ToolError: If tool initialization fails
        """
        if tool_id not in self._tools:
            with self._lock:
                if tool_id not in self._tools:
                    try:
                        logger.info("Initializing tool: %s", tool_id)
                        schema_dir = Path(__file__).parent / "schemas"
                        logger.info("Schema directory: %s", schema_dir)
                        schema_path = schema_dir / f"{tool_id}.json"
                        logger.info("Schema path: %s", schema_path)
                        logger.info("Schema exists: %s", schema_path.exists())

                        handler: ToolHandler
                        if tool_id == "list":
                            logger.info("Creating ListTool instance")
                            handler = ListTool(schema_path)
                            logger.info("ListTool instance created")
                        elif tool_id == "search":
                            logger.info("Creating SearchTool instance")
                            handler = SearchTool(schema_path, self._get_vector_store())
                            logger.info("SearchTool instance created")
                        elif tool_id == "extract":
                            logger.info("Creating ExtractTool instance")
                            handler = ExtractTool(schema_path)
                            logger.info("ExtractTool instance created")
                        elif tool_id == "remove":
                            logger.info("Creating RemoveTool instance")
                            handler = RemoveTool(schema_path)
                            logger.info("RemoveTool instance created")
                        else:
                            raise ToolError(f"Unknown tool ID: {tool_id}")

                        logger.info("Registering tool: %s", tool_id)
                        self.register_tool(handler)
                        logger.info("Tool initialized successfully: %s", tool_id)
                    except Exception as e:
                        self._state = ServerState.ERROR
                        raise ToolError(
                            f"Failed to initialize tool {tool_id}: {str(e)}"
                        ) from e

    def register_resource(self, resource: ResourceHandler) -> None:
        """Register a resource handler.

        Args:
            resource: Resource handler to register
        """
        metadata = resource.get_metadata()
        self._resources[metadata["id"]] = resource

    def register_tool(self, tool: ToolHandler) -> None:
        """Register a tool handler.

        Args:
            tool: Tool handler to register

        Raises:
            ToolError: If tool registration fails
        """
        try:
            metadata = tool.get_metadata()
            if metadata["id"] in self._tools:
                raise ToolError(f"Tool {metadata['id']} already registered")
            self._tools[metadata["id"]] = tool
            self._state = ServerState.READY
            logger.info("Registered tool: %s", metadata["id"])
        except Exception as e:
            self._state = ServerState.ERROR
            raise ToolError(f"Failed to register tool: {str(e)}") from e

    def start(self) -> None:
        """Start the server.

        Raises:
            MCPError: If server fails to start or is in an invalid state
        """
        if self._state == ServerState.ERROR:
            raise MCPError("Cannot start server in ERROR state")

        with self._lock:
            try:
                logger.info("Starting server...")
                self._state = ServerState.INITIALIZING
                # Resources and tools will be initialized lazily when needed
                self._state = ServerState.READY
                logger.info("Server started successfully")
            except Exception as e:
                self._state = ServerState.ERROR
                raise MCPError(f"Failed to start server: {str(e)}") from e

    def stop(self) -> None:
        """Stop the server and clean up resources.

        Raises:
            MCPError: If server fails to stop or is in an invalid state
        """
        if self._state == ServerState.ERROR:
            raise MCPError("Cannot stop server in ERROR state")

        with self._lock:
            try:
                logger.info("Stopping server...")
                self._cleanup_resources()
                self._resources.clear()
                self._tools.clear()
                self._note_store = None
                self._attachment_store = None
                self._vector_store = None
                self._resources_initialized = False
                self._tools_initialized = False
                self._state = ServerState.SHUTDOWN
                logger.info("Server stopped successfully")
            except Exception as e:
                self._state = ServerState.ERROR
                raise MCPError(f"Failed to stop server: {str(e)}") from e

    def get_resources(self) -> list[ResourceMetadata]:
        """Get list of registered resource metadata."""
        # Initialize core resources
        for resource_id in ["notes", "attachments", "vectors"]:
            self._ensure_resource(resource_id)
        return [resource.get_metadata() for resource in self._resources.values()]

    def get_tools(self) -> list[ToolMetadata]:
        """Get list of registered tool metadata."""
        # Initialize core tools
        for tool_id in ["list", "search", "extract", "remove"]:
            self._ensure_tool(tool_id)
        return [tool.get_metadata() for tool in self._tools.values()]

    def _cleanup_resources(self) -> None:
        """Clean up resources and tools before stopping the server."""
        for resource in self._resources.values():
            resource.cleanup()
        for tool in self._tools.values():
            tool.cleanup()
