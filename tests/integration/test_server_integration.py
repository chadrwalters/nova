"""Integration tests for Nova MCP server."""

from pathlib import Path

import pytest
from nova.server.server import NovaServer
from nova.server.types import MCPError, ServerConfig, ServerState


@pytest.fixture
def nova_dir(temp_dir: Path) -> Path:
    """Create Nova directory structure.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to Nova directory
    """
    nova_dir = temp_dir / ".nova"
    subdirs = ["vector_store", "notes", "attachments", "ocr"]
    for subdir in subdirs:
        (nova_dir / subdir).mkdir(parents=True, exist_ok=True)
    return nova_dir


def test_server_lifecycle(nova_dir: Path) -> None:
    """Test complete server lifecycle."""
    # Create server
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)
    server = NovaServer(config)
    assert server.state == ServerState.INITIALIZING

    # Start server
    server.start()
    assert server.state == ServerState.READY

    # Verify resources are initialized
    resources = server.get_resources()  # type: ignore[unreachable]  # mypy is wrong here, the code is reachable
    resource_ids = {r["id"] for r in resources}
    assert "vector-store" in resource_ids
    assert "notes" in resource_ids
    assert "attachment-handler" in resource_ids
    assert "ocr-handler" in resource_ids

    # Verify tools are initialized
    tools = server.get_tools()
    tool_ids = {t["id"] for t in tools}
    assert "search-tool" in tool_ids
    assert "list" in tool_ids
    assert "extract" in tool_ids
    assert "remove" in tool_ids

    # Stop server
    server.stop()
    assert server.state == ServerState.SHUTDOWN

    # Verify can recover through restart
    server.stop()
    server.start()
    assert server.state == ServerState.READY

    # Clean up
    server.stop()


def test_resource_persistence(nova_dir: Path) -> None:
    """Test resource state persistence."""
    # Create and start first server instance
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)
    server1 = NovaServer(config)
    server1.start()

    # Get initial resource state
    resources1 = {r["id"]: r for r in server1.get_resources()}
    server1.stop()

    # Create and start second server instance
    server2 = NovaServer(config)
    server2.start()

    # Get new resource state
    resources2 = {r["id"]: r for r in server2.get_resources()}

    # Compare states
    assert set(resources1.keys()) == set(resources2.keys())
    for resource_id in resources1:
        r1 = resources1[resource_id]
        r2 = resources2[resource_id]
        assert r1["type"] == r2["type"]
        assert r1["name"] == r2["name"]
        assert r1["version"] == r2["version"]

    server2.stop()


def test_concurrent_operations(nova_dir: Path) -> None:
    """Test concurrent server operations."""
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)

    # Create multiple server instances
    servers = [NovaServer(config) for _ in range(3)]

    # Start all servers
    for server in servers:
        server.start()
        assert server.state == ServerState.READY

    # Verify resource consistency
    resource_sets = [
        {(r["id"], r["type"], r["name"], r["version"]) for r in server.get_resources()}
        for server in servers
    ]
    assert all(s == resource_sets[0] for s in resource_sets)

    # Verify tool consistency
    tool_sets = [
        {(t["id"], t["type"], t["name"], t["version"]) for t in server.get_tools()}
        for server in servers
    ]
    assert all(s == tool_sets[0] for s in tool_sets)

    # Stop all servers
    for server in servers:
        server.stop()
        assert server.state == ServerState.SHUTDOWN


def test_error_recovery(nova_dir: Path) -> None:
    """Test server error recovery."""
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)
    server = NovaServer(config)

    # Start server normally
    server.start()
    assert server.state == ServerState.READY

    # Force error state
    server._state = ServerState.ERROR

    # Verify cannot stop in error state
    with pytest.raises(MCPError, match="Cannot stop server in ERROR state"):
        server.stop()

    # Verify cannot start in error state
    with pytest.raises(MCPError, match="Cannot start server in ERROR state"):
        server.start()

    # Reset state and verify can start again
    server._state = ServerState.INITIALIZING
    server.start()
    assert server.state == ServerState.READY

    # Clean up
    server.stop()
