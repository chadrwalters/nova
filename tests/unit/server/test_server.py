"""Unit tests for Nova MCP server."""

import time
from pathlib import Path
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from nova.server.attachments import AttachmentStore
from nova.server.server import NovaServer
from nova.server.types import (
    MCPError,
    ProtocolError,
    ResourceError,
    ResourceType,
    ServerConfig,
    ServerState,
    ToolError,
)
from nova.stubs.docling import Document, DocumentConverter
from nova.vector_store.store import VectorStore


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create a mock vector store.

    Returns:
        MagicMock: Mocked vector store instance
    """
    mock = MagicMock(spec=VectorStore)
    mock._store_dir = Path("/mock/store")
    mock.client = MagicMock()
    mock.get_metadata.return_value = {
        "id": "vector_store",
        "name": "Vector Store",
        "version": "1.0.0",
        "modified": time.time(),
        "total_vectors": 0,
        "store_dir": "/mock/store",
    }
    mock.cleanup = MagicMock()
    return mock


@pytest.fixture
def mock_note_store() -> MagicMock:
    """Create a mock note store.

    Returns:
        MagicMock: Mocked note store instance
    """
    mock = MagicMock(spec=DocumentConverter)
    mock.input_dir = "/mock/input"
    mock.convert_all.return_value = []
    mock.convert_file.return_value = Document("test.md")
    mock.get_metadata = MagicMock(
        return_value={
            "id": "notes",
            "type": ResourceType.NOTE.name,
            "name": "Note Store",
            "version": "0.1.0",
            "modified": time.time(),
            "attributes": {
                "total_notes": 0,
                "total_tags": 0,
                "formats": ["markdown"],
            },
        }
    )
    return mock


@pytest.fixture
def mock_attachment_store() -> MagicMock:
    """Create a mock attachment store.

    Returns:
        MagicMock: Mocked attachment store instance
    """
    mock = MagicMock(spec=AttachmentStore)
    mock.count_attachments.return_value = 0
    mock.mime_types = ["png", "jpg", "jpeg", "pdf", "tiff"]
    mock.storage_path = Path("/test/store")
    mock.get_metadata = MagicMock(
        return_value={
            "id": "attachments",
            "type": ResourceType.ATTACHMENT.name,
            "name": "Attachment Store",
            "version": "1.0.0",
            "modified": time.time(),
            "attributes": {
                "total_attachments": 0,
                "mime_types": ["png", "jpg", "jpeg", "pdf", "tiff"],
            },
        }
    )
    return mock


@pytest.fixture
def mock_schema_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary schema directory with mock schema files.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path: Path to the mock schema directory
    """
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()

    # Create mock schema files
    mock_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for tool in ["list", "search", "extract", "remove"]:
        schema_file = schema_dir / f"{tool}.json"
        schema_file.write_text(str(mock_schema))

    yield schema_dir


def test_server_initialization(server_config: ServerConfig) -> None:
    """Test server initialization.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)
    assert server.state == ServerState.INITIALIZING


def test_server_start_stop(
    server_config: ServerConfig,
    mock_vector_store: MagicMock,
    mock_note_store: MagicMock,
    mock_attachment_store: MagicMock,
    mock_schema_dir: Path,
) -> None:
    """Test server start and stop.

    Args:
        server_config: Server configuration fixture
        mock_vector_store: Mock vector store fixture
        mock_note_store: Mock note store fixture
        mock_attachment_store: Mock attachment store fixture
        mock_schema_dir: Mock schema directory fixture
    """
    # Mock tool handlers
    mock_list_tool = MagicMock()
    mock_list_tool.get_metadata.return_value = {
        "id": "list",
        "type": "test",
        "name": "List Tool",
        "version": "1.0.0",
        "parameters": {},
        "capabilities": [],
    }
    mock_list_tool.schema_path = mock_schema_dir / "list.json"

    mock_search_tool = MagicMock()
    mock_search_tool.get_metadata.return_value = {
        "id": "search",
        "type": "test",
        "name": "Search Tool",
        "version": "1.0.0",
        "parameters": {},
        "capabilities": [],
    }
    mock_search_tool.schema_path = mock_schema_dir / "search.json"

    mock_extract_tool = MagicMock()
    mock_extract_tool.get_metadata.return_value = {
        "id": "extract",
        "type": "test",
        "name": "Extract Tool",
        "version": "1.0.0",
        "parameters": {},
        "capabilities": [],
    }
    mock_extract_tool.schema_path = mock_schema_dir / "extract.json"

    mock_remove_tool = MagicMock()
    mock_remove_tool.get_metadata.return_value = {
        "id": "remove",
        "type": "test",
        "name": "Remove Tool",
        "version": "1.0.0",
        "parameters": {},
        "capabilities": [],
    }
    mock_remove_tool.schema_path = mock_schema_dir / "remove.json"

    with (
        patch(
            "nova.server.server.NovaServer._get_vector_store",
            return_value=mock_vector_store,
        ),
        patch(
            "nova.server.server.NovaServer._get_note_store",
            return_value=mock_note_store,
        ),
        patch(
            "nova.server.server.NovaServer._get_attachment_store",
            return_value=mock_attachment_store,
        ),
        patch("nova.server.tools.ListTool", return_value=mock_list_tool),
        patch("nova.server.tools.SearchTool", return_value=mock_search_tool),
        patch("nova.server.tools.ExtractTool", return_value=mock_extract_tool),
        patch("nova.server.tools.RemoveTool", return_value=mock_remove_tool),
        patch("nova.server.server.Path", return_value=mock_schema_dir),
    ):
        server = NovaServer(server_config)
        server.start()
        assert server._state == ServerState.READY

        server.stop()
        assert server._state == ServerState.SHUTDOWN


def test_invalid_configuration() -> None:
    """Test server initialization with invalid configuration."""
    # Test empty host
    with pytest.raises(ProtocolError, match="Server host not configured"):
        NovaServer(
            ServerConfig(
                host="",
                port=8000,
                input_dir="/test/input",
                store_dir="/test/store",
                debug=False,
                max_connections=5,
            )
        )

    # Test invalid port
    with pytest.raises(ProtocolError, match="Server port must be greater than 0"):
        NovaServer(
            ServerConfig(
                host="localhost",
                port=0,
                input_dir="/test/input",
                store_dir="/test/store",
                debug=False,
                max_connections=5,
            )
        )

    # Test invalid max connections
    with pytest.raises(
        ProtocolError, match="Maximum connections must be greater than 0"
    ):
        NovaServer(
            ServerConfig(
                host="localhost",
                port=8000,
                input_dir="/test/input",
                store_dir="/test/store",
                debug=False,
                max_connections=0,
            )
        )


def test_resource_registration(server_config: ServerConfig) -> None:
    """Test resource registration.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)

    # Create mock resource
    mock_resource = MagicMock()
    mock_resource.get_metadata.return_value = {
        "id": "test_resource",
        "type": "test",
        "name": "Test Resource",
        "version": "1.0.0",
        "modified": 0,
        "attributes": {},
    }

    # Test registration
    server.register_resource(mock_resource)
    resources = server.get_resources()

    # Find our test resource
    test_resource = next((r for r in resources if r["id"] == "test_resource"), None)
    assert test_resource is not None
    assert test_resource["id"] == "test_resource"
    assert test_resource["name"] == "Test Resource"


def test_tool_registration(server_config: ServerConfig) -> None:
    """Test tool registration.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)

    # Create mock tool
    mock_tool = MagicMock()
    mock_tool.get_metadata.return_value = {
        "id": "test_tool",
        "type": "test",
        "name": "Test Tool",
        "version": "1.0.0",
        "parameters": {},
        "capabilities": [],
    }
    mock_tool.schema_path = Path("/mock/schemas/test.json")

    # Test registration
    server.register_tool(mock_tool)
    tools = server.get_tools()

    # Find our test tool
    test_tool = next((t for t in tools if t["id"] == "test_tool"), None)
    assert test_tool is not None
    assert test_tool["id"] == "test_tool"
    assert test_tool["name"] == "Test Tool"


def test_resource_registration_failure(server_config: ServerConfig) -> None:
    """Test resource registration failure.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)

    # Create mock resource that raises error
    mock_resource = MagicMock()
    mock_resource.get_metadata.side_effect = ResourceError("Failed to get metadata")

    # Test registration failure
    with pytest.raises(ResourceError):
        server.register_resource(mock_resource)


def test_tool_registration_failure(server_config: ServerConfig) -> None:
    """Test tool registration failure.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)

    # Create mock tool that raises error
    mock_tool = MagicMock()
    mock_tool.get_metadata.side_effect = ToolError("Failed to get metadata")

    # Test registration failure
    with pytest.raises(ToolError):
        server.register_tool(mock_tool)


def test_server_start_failure(server_config: ServerConfig) -> None:
    """Test server start failure.

    Args:
        server_config: Server configuration fixture
    """
    server = NovaServer(server_config)
    server._state = ServerState.ERROR

    with pytest.raises(MCPError, match="Cannot start server in ERROR state"):
        server.start()


def test_server_stop_failure(
    server_config: ServerConfig,
    mock_vector_store: MagicMock,
    mock_note_store: MagicMock,
    mock_attachment_store: MagicMock,
) -> None:
    """Test server stop failure.

    Args:
        server_config: Server configuration fixture
        mock_vector_store: Mock vector store fixture
        mock_note_store: Mock note store fixture
        mock_attachment_store: Mock attachment store fixture
    """
    server = NovaServer(server_config)
    server._state = ServerState.ERROR

    with pytest.raises(MCPError, match="Cannot stop server in ERROR state"):
        server.stop()
