"""Unit tests for Nova MCP server."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
from nova.vector_store.store import VectorStore


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create a mock vector store."""
    mock = MagicMock(spec=VectorStore)
    mock._store_dir = Path("/mock/store")
    mock.client = MagicMock()
    mock.get_metadata.return_value = {
        "id": "vector_store",
        "name": "Vector Store",
        "version": "1.0.0",
        "store_dir": "/mock/store",
    }
    return mock


def test_server_initialization(server_config: ServerConfig) -> None:
    """Test server initialization."""
    server = NovaServer(server_config)
    assert server.state == ServerState.INITIALIZING


def test_server_start_stop(
    server_config: ServerConfig,
    mock_vector_store: MagicMock,
    mock_note_store: MagicMock,
    mock_attachment_store: MagicMock,
    mock_ocr_engine: MagicMock,
) -> None:
    """Test server start and stop."""
    # Configure mocks to return proper metadata
    mock_vector_store.get_metadata.return_value = {
        "id": "vector-store",
        "type": ResourceType.VECTOR_STORE.name,
        "name": "Vector Store",
        "version": "1.0.0",
        "modified": time.time(),
        "total_vectors": 0,
        "total_chunks": 0,
        "total_bytes": 0,
        "collection_name": "nova",
        "embedding_dimension": 384,
        "index_type": "HNSW",
    }
    mock_note_store.get_metadata.return_value = {
        "id": "notes",
        "type": ResourceType.NOTE.name,
        "name": "Note Store",
        "version": "0.1.0",
        "modified": time.time(),
        "attributes": {"total_notes": 0, "total_tags": 0, "formats": ["markdown"]},
    }
    mock_attachment_store.get_metadata.return_value = {
        "id": "attachment-handler",
        "type": ResourceType.ATTACHMENT.name,
        "name": "Attachment Handler",
        "version": "1.0.0",
        "modified": time.time(),
        "attributes": {
            "total_attachments": 0,
            "total_bytes": 0,
            "supported_formats": ["png", "jpg", "jpeg", "pdf", "tiff"],
            "storage_path": "/test/store",
        },
    }
    mock_ocr_engine.get_metadata.return_value = {
        "id": "ocr-handler",
        "type": ResourceType.OCR.name,
        "name": "OCR Handler",
        "version": "0.1.0",
        "modified": time.time(),
        "attributes": {
            "engine": "gpt-4o",
            "languages": ["eng"],
            "confidence_threshold": 0.8,
            "cache_enabled": True,
            "cache_size": 1000,
            "supported_formats": ["png", "jpg", "pdf"],
        },
    }

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
        patch(
            "nova.server.server.NovaServer._get_ocr_engine",
            return_value=mock_ocr_engine,
        ),
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
        NovaServer(ServerConfig(host="", port=8000, debug=False, max_connections=5))

    # Test invalid port
    with pytest.raises(ProtocolError, match="Server port must be greater than 0"):
        NovaServer(
            ServerConfig(host="localhost", port=0, debug=False, max_connections=5)
        )

    # Test invalid max connections
    with pytest.raises(
        ProtocolError, match="Maximum connections must be greater than 0"
    ):
        NovaServer(
            ServerConfig(host="localhost", port=8000, debug=False, max_connections=0)
        )


def test_resource_registration(server_config: ServerConfig) -> None:
    """Test resource registration."""
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
    assert len(resources) == 1
    assert resources[0]["id"] == "test_resource"


def test_tool_registration(server_config: ServerConfig) -> None:
    """Test tool registration."""
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

    # Test registration
    server.register_tool(mock_tool)
    tools = server.get_tools()
    assert len(tools) == 1
    assert tools[0]["id"] == "test_tool"


def test_resource_registration_failure(server_config: ServerConfig) -> None:
    """Test resource registration failure."""
    server = NovaServer(server_config)

    # Create failing mock resource
    mock_resource = MagicMock()
    mock_resource.get_metadata.side_effect = Exception("Test error")

    # Test registration failure
    with pytest.raises(ResourceError):
        server.register_resource(mock_resource)


def test_tool_registration_failure(server_config: ServerConfig) -> None:
    """Test tool registration failure."""
    server = NovaServer(server_config)

    # Create failing mock tool
    mock_tool = MagicMock()
    mock_tool.get_metadata.side_effect = Exception("Test error")

    # Test registration failure
    with pytest.raises(ToolError):
        server.register_tool(mock_tool)


def test_server_start_failure(server_config: ServerConfig) -> None:
    """Test server start failure."""
    server = NovaServer(server_config)

    # Mock resource initialization to fail
    with patch(
        "nova.server.server.NovaServer._initialize_resources",
        side_effect=MCPError("Test error"),
    ):
        # Test start failure
        with pytest.raises(MCPError):
            server.start()
        assert server.state == ServerState.ERROR


def test_server_stop_failure(
    server_config: ServerConfig,
    mock_vector_store: MagicMock,
    mock_note_store: MagicMock,
    mock_attachment_store: MagicMock,
) -> None:
    """Test server stop failure."""
    # Configure mocks to return proper metadata
    mock_vector_store.get_metadata.return_value = {
        "id": "vector-store",
        "type": ResourceType.VECTOR_STORE.name,
        "name": "Vector Store",
        "version": "1.0.0",
        "modified": time.time(),
        "total_vectors": 0,
        "total_chunks": 0,
        "total_bytes": 0,
        "collection_name": "nova",
        "embedding_dimension": 384,
        "index_type": "HNSW",
    }
    mock_note_store.get_metadata.return_value = {
        "id": "notes",
        "type": ResourceType.NOTE.name,
        "name": "Note Store",
        "version": "0.1.0",
        "modified": time.time(),
        "attributes": {"total_notes": 0, "total_tags": 0, "formats": ["markdown"]},
    }
    mock_attachment_store.get_metadata.return_value = {
        "id": "attachment-handler",
        "type": ResourceType.ATTACHMENT.name,
        "name": "Attachment Handler",
        "version": "1.0.0",
        "modified": time.time(),
        "attributes": {
            "total_attachments": 0,
            "total_bytes": 0,
            "supported_formats": ["png", "jpg", "jpeg", "pdf", "tiff"],
            "storage_path": "/test/store",
        },
    }

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
    ):
        server = NovaServer(server_config)
        server.start()

        # Mock cleanup to fail
        with patch(
            "nova.server.server.NovaServer._cleanup_resources",
            side_effect=MCPError("Test error"),
        ):
            # Test stop failure
            with pytest.raises(MCPError):
                server.stop()
            assert server.state == ServerState.ERROR
