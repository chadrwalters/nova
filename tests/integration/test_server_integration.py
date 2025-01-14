"""Integration tests for Nova MCP server."""

from pathlib import Path
import logging
from collections.abc import Generator
import pytest
from docling_core.types.doc import (
    DoclingDocument,
    TextItem,
    DocItemLabel,
    GroupItem,
    GroupLabel,
)

from nova.server.server import NovaServer
from nova.server.types import MCPError, ServerConfig, ServerState

logger = logging.getLogger(__name__)


@pytest.fixture
def test_document(nova_dir: Path) -> Generator[DoclingDocument, None, None]:
    """Create a test document.

    Args:
        nova_dir: Nova directory fixture

    Returns:
        Test document
    """
    text_item = TextItem(
        self_ref="#/texts/0",
        label=DocItemLabel.TEXT,
        orig="This is a test note",
        text="This is a test note",
        prov=[],
    )

    furniture = GroupItem(
        self_ref="#/furniture", label=GroupLabel.UNSPECIFIED, children=[]
    )

    body = GroupItem(self_ref="#/body", label=GroupLabel.UNSPECIFIED, children=[])

    doc = DoclingDocument(
        name="test_note",
        metadata={
            "tags": ["test", "integration"],
            "created": "2024-01-13T00:00:00Z",
            "modified": "2024-01-13T00:00:00Z",
        },
    )

    # Add components to document
    doc.texts = [text_item]
    doc.furniture = furniture
    doc.body = body
    doc.groups = []
    doc.pages = {}
    doc.pictures = []
    doc.key_value_items = []

    # Save document
    input_dir = nova_dir / "notes"
    input_dir.mkdir(parents=True, exist_ok=True)
    doc_path = input_dir / "test_note.md"
    doc_path.write_text(text_item.text)

    yield doc


@pytest.fixture
def nova_dir(temp_dir: Path) -> Path:
    """Create Nova directory structure.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to Nova directory
    """
    nova_dir = temp_dir / ".nova"
    subdirs = ["vector_store", "notes", "attachments"]
    for subdir in subdirs:
        (nova_dir / subdir).mkdir(parents=True, exist_ok=True)
    return nova_dir


@pytest.fixture
def server(
    nova_dir: Path, test_document: DoclingDocument
) -> Generator[NovaServer, None, None]:
    """Create and cleanup server instance.

    Args:
        nova_dir: Nova directory fixture
        test_document: Test document fixture

    Returns:
        Server instance that will be cleaned up after test
    """
    config = ServerConfig(
        host="localhost",
        port=8000,
        debug=True,
        max_connections=5,
        input_dir=str(nova_dir / "notes"),
        store_dir=str(nova_dir),
    )
    server = NovaServer(config)
    logger.info("Created server instance")

    # Initialize resources explicitly
    server._ensure_resource("notes")
    server._ensure_resource("attachments")
    server._ensure_resource("vectors")

    yield server

    # Cleanup
    try:
        if server.state != ServerState.SHUTDOWN:
            logger.info("Stopping server in cleanup")
            # Reset state to READY if in ERROR state
            if server.state == ServerState.ERROR:
                server._state = ServerState.READY
            server.stop()
    except Exception as e:
        logger.error("Error stopping server: %s", e)
        # Force state to SHUTDOWN
        server._state = ServerState.SHUTDOWN


def test_server_lifecycle(server: NovaServer) -> None:
    """Test complete server lifecycle."""
    logger.info("Starting lifecycle test")
    assert server.state == ServerState.INITIALIZING

    # Start server
    logger.info("Starting server")
    server.start()
    logger.info("Server started")
    assert server.state == ServerState.READY

    # Verify resources are initialized
    resources = server.get_resources()
    resource_ids = {r.get("id") for r in resources}
    assert "vector-store" in resource_ids
    assert "notes" in resource_ids
    assert "attachments" in resource_ids

    # Verify tools are initialized
    tools = server.get_tools()
    tool_ids = {t.get("id") for t in tools}
    assert "search" in tool_ids
    assert "list" in tool_ids
    assert "extract" in tool_ids
    assert "remove" in tool_ids

    # Stop server
    logger.info("Stopping server")
    server.stop()
    logger.info("Server stopped")
    assert server.state == ServerState.SHUTDOWN


def test_resource_persistence(nova_dir: Path, test_document: DoclingDocument) -> None:
    """Test resource state persistence."""
    logger.info("Starting persistence test")
    # Create and start first server instance
    config = ServerConfig(
        host="localhost",
        port=8001,
        debug=True,
        max_connections=5,
        input_dir=str(nova_dir / "notes"),
        store_dir=str(nova_dir),
    )
    server1 = NovaServer(config)
    logger.info("Starting first server")
    server1.start()
    logger.info("First server started")

    # Get initial resource state
    resources1 = {r.get("id"): r for r in server1.get_resources()}
    logger.info("Stopping first server")
    server1.stop()
    logger.info("First server stopped")

    # Create and start second server instance
    server2 = NovaServer(config)
    logger.info("Starting second server")
    server2.start()
    logger.info("Second server started")

    # Get new resource state
    resources2 = {r.get("id"): r for r in server2.get_resources()}

    # Compare states
    assert set(resources1.keys()) == set(resources2.keys())
    for resource_id in resources1:
        r1 = resources1[resource_id]
        r2 = resources2[resource_id]
        assert r1.get("type") == r2.get("type")
        assert r1.get("name") == r2.get("name")
        assert r1.get("version") == r2.get("version")

    logger.info("Stopping second server")
    server2.stop()
    logger.info("Second server stopped")


def test_concurrent_operations(nova_dir: Path, test_document: DoclingDocument) -> None:
    """Test concurrent server operations."""
    logger.info("Starting concurrent operations test")
    # Create multiple server instances with different ports
    servers = []
    for i in range(3):
        config = ServerConfig(
            host="localhost",
            port=8002 + i,
            debug=True,
            max_connections=5,
            input_dir=str(nova_dir / "notes"),
            store_dir=str(nova_dir),
        )
        server = NovaServer(config)
        servers.append(server)
        logger.info("Created server %d", i)

    try:
        # Start all servers
        for i, server in enumerate(servers):
            logger.info("Starting server %d", i)
            server.start()
            logger.info("Server %d started", i)
            assert server.state == ServerState.READY

        # Verify resource consistency
        resource_sets = [
            {
                (r.get("id"), r.get("type"), r.get("name"), r.get("version"))
                for r in server.get_resources()
            }
            for server in servers
        ]
        assert all(s == resource_sets[0] for s in resource_sets)

        # Verify tool consistency
        tool_sets = [
            {
                (t.get("id"), t.get("type"), t.get("name"), t.get("version"))
                for t in server.get_tools()
            }
            for server in servers
        ]
        assert all(s == tool_sets[0] for s in tool_sets)
    finally:
        # Stop all servers
        for i, server in enumerate(servers):
            try:
                if server.state != ServerState.SHUTDOWN:
                    logger.info("Stopping server %d", i)
                    server.stop()
                    logger.info("Server %d stopped", i)
            except Exception as e:
                logger.error("Error stopping server %d: %s", i, e)


def test_error_recovery(server: NovaServer) -> None:
    """Test server error recovery."""
    logger.info("Starting error recovery test")
    # Start server normally
    logger.info("Starting server")
    server.start()
    logger.info("Server started")
    assert server.state == ServerState.READY

    # Force error state
    logger.info("Forcing error state")
    server._state = ServerState.ERROR

    # Verify cannot stop in error state
    with pytest.raises(MCPError, match="Cannot stop server in ERROR state"):
        server.stop()

    # Verify cannot start in error state
    with pytest.raises(MCPError, match="Cannot start server in ERROR state"):
        server.start()

    # Reset state and verify can start again
    logger.info("Resetting state")
    server._state = ServerState.INITIALIZING
    logger.info("Starting server again")
    server.start()
    logger.info("Server started")
    assert server.state == ServerState.READY
