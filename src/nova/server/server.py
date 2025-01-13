"""Nova MCP Server implementation."""

import logging
from pathlib import Path
from collections.abc import Sequence

from nova.bear_parser.ocr import EasyOcrModel
from nova.bear_parser.parser import BearParser
from nova.server.attachments import AttachmentStore
from nova.server.resources import (
    AttachmentHandler,
    NoteHandler,
    OCRHandler,
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

            # Initialize OCR handler
            ocr_engine = self._get_ocr_engine()
            self.register_resource(OCRHandler(ocr_engine))

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
            attachments_dir = Path(".nova/attachments")
            attachments_dir.mkdir(parents=True, exist_ok=True)
            return AttachmentStore(attachments_dir)
        except Exception as e:
            raise ResourceError(
                f"Failed to initialize attachment store: {str(e)}"
            ) from e

    def _get_ocr_engine(self) -> EasyOcrModel:
        """Get OCR engine instance.

        Returns:
            Initialized OCR engine instance

        Raises:
            ResourceError: If OCR engine initialization fails
        """
        try:
            ocr_dir = Path(".nova/ocr")
            ocr_dir.mkdir(parents=True, exist_ok=True)
            return EasyOcrModel()
        except Exception as e:
            raise ResourceError(f"Failed to initialize OCR engine: {str(e)}") from e

    def _initialize_tools(self) -> None:
        """Initialize tool handlers.

        Raises:
            ToolError: If tool initialization fails
        """
        logger.info("Initializing tools")
        try:
            # Get schema paths from source
            schema_dir = Path(__file__).parent / "schemas"
            if not schema_dir.exists():
                raise ToolError("Schema directory not found")

            # Initialize search tool with vector store
            vector_store = self._get_vector_store()
            search_schema = schema_dir / "search_tool.json"
            self.register_tool(SearchTool(search_schema, vector_store))

            # Initialize list tool
            list_schema = schema_dir / "list_tool.json"
            self.register_tool(ListTool(list_schema))

            # Initialize extract tool
            extract_schema = schema_dir / "extract_tool.json"
            self.register_tool(ExtractTool(extract_schema))

            # Initialize remove tool
            remove_schema = schema_dir / "remove_tool.json"
            self.register_tool(RemoveTool(remove_schema))

            logger.info("Tool initialization complete")
        except Exception as e:
            raise ToolError(f"Failed to initialize tools: {str(e)}") from e

    def _cleanup_resources(self) -> None:
        """Cleanup resource handlers.

        Raises:
            ResourceError: If resource cleanup fails
        """
        logger.info("Cleaning up resources")
        try:
            # Clean up vector store
            if "vector_store" in self._resources:
                vector_store = self._get_vector_store()
                vector_store.client.reset()  # Reset Chroma client
                logger.info("Cleaned up vector store")

            # Clean up note store
            if "notes" in self._resources:
                # Note store is read-only, no cleanup needed
                logger.info("Note store is read-only, no cleanup needed")

            # Clean up attachment store
            if "attachments" in self._resources:
                attachment_store = self._get_attachment_store()
                attachment_store.clear()
                logger.info("Cleaned up attachment store")

            # Clean up OCR engine
            if "ocr" in self._resources:
                # OCR engine is stateless, no cleanup needed
                logger.info("OCR engine is stateless, no cleanup needed")

            # Clear all resource registrations
            self._resources.clear()
            logger.info("Resource cleanup complete")
        except Exception as e:
            raise ResourceError(f"Failed to cleanup resources: {str(e)}") from e

    def _cleanup_tools(self) -> None:
        """Cleanup tool registry.

        Raises:
            ToolError: If tool cleanup fails
        """
        logger.info("Cleaning up tools")
        try:
            # Tools are stateless, just clear registrations
            self._tools.clear()
            logger.info("Tool cleanup complete")
        except Exception as e:
            raise ToolError(f"Failed to cleanup tools: {str(e)}") from e
