"""Unit tests for WebSocket server."""

from datetime import datetime, timedelta
from collections.abc import Callable
import pytest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from nova.server.protocol.websocket import NovaWebSocketServer
from nova.server.types import (
    ResourceHandler,
    ResourceError,
    ResourceMetadata,
    ResourceType,
)


class MockResourceHandler(ResourceHandler):
    """Mock resource handler for testing."""

    def __init__(self) -> None:
        """Initialize mock resource handler."""
        self._callbacks: list[Callable[[], None]] = []
        self._metadata: ResourceMetadata = {
            "id": "test-resource",
            "type": ResourceType.NOTE,
            "name": "Test Resource",
            "version": "0.1.0",
            "modified": datetime.now().timestamp(),
            "attributes": {},
        }

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return self._metadata

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation."""
        return operation in ["read", "write", "delete"]

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback."""
        self._callbacks.append(callback)

    def trigger_change(self) -> None:
        """Trigger change callbacks."""
        for callback in self._callbacks:
            callback()


@pytest.fixture
def mock_handler() -> MockResourceHandler:
    """Create mock resource handler."""
    return MockResourceHandler()


@pytest.fixture
def resources(mock_handler: MockResourceHandler) -> dict[str, ResourceHandler]:
    """Create resource dictionary."""
    return {"test-resource": mock_handler}


@pytest.fixture
def server(resources: dict[str, ResourceHandler]) -> NovaWebSocketServer:
    """Create WebSocket server."""
    return NovaWebSocketServer(
        api_key="test-key", resources=resources, cors_origins=["http://localhost:3000"]
    )


@pytest.fixture
def client(server: NovaWebSocketServer) -> TestClient:
    """Create test client."""
    return TestClient(server.app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["timestamp"], str)


@pytest.mark.asyncio
async def test_websocket_connection(server: NovaWebSocketServer) -> None:
    """Test WebSocket connection."""
    client_id = "test-client"

    # Create mock WebSocket
    websocket = Mock(spec=WebSocket)
    websocket.headers = {"x-api-key": "test-key"}

    # Connect
    await server.manager.connect(websocket, client_id)
    assert client_id in server.manager.active_connections
    assert client_id in server.manager._rate_limits

    # Disconnect
    server.manager.disconnect(client_id)
    assert client_id not in server.manager.active_connections
    assert client_id not in server.manager._rate_limits


@pytest.mark.asyncio
async def test_websocket_subscribe(server: NovaWebSocketServer) -> None:
    """Test WebSocket subscription."""
    client_id = "test-client"
    resource_id = "test-resource"

    # Subscribe
    server.manager.subscribe(client_id, resource_id)
    assert client_id in server.manager.subscriptions[resource_id]

    # Unsubscribe
    server.manager.unsubscribe(client_id, resource_id)
    assert resource_id not in server.manager.subscriptions


@pytest.mark.asyncio
async def test_websocket_broadcast(server: NovaWebSocketServer) -> None:
    """Test WebSocket broadcast."""
    client_id = "test-client"
    resource_id = "test-resource"

    # Create mock WebSocket
    websocket = Mock(spec=WebSocket)
    websocket.send_json = Mock()

    # Connect and subscribe
    await server.manager.connect(websocket, client_id)
    server.manager.subscribe(client_id, resource_id)

    # Broadcast message
    message = {"type": "test", "data": "test"}
    await server.manager.broadcast(resource_id, message)

    # Verify message sent
    websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_rate_limit(server: NovaWebSocketServer) -> None:
    """Test rate limiting."""
    client_id = "test-client"

    # Test within limit
    for _ in range(server.manager.MAX_REQUESTS_PER_MINUTE - 1):
        assert server.manager.check_rate_limit(client_id)

    # Test at limit
    assert server.manager.check_rate_limit(client_id)
    assert not server.manager.check_rate_limit(client_id)

    # Test expiration
    timestamps = server.manager._rate_limits[client_id]
    timestamps[0] = datetime.now() - timedelta(minutes=2)
    assert server.manager.check_rate_limit(client_id)


@pytest.mark.asyncio
async def test_handle_message_subscribe(
    server: NovaWebSocketServer, mock_handler: MockResourceHandler
) -> None:
    """Test message handling for subscribe action."""
    client_id = "test-client"
    message = {"action": "subscribe", "resource_id": "test-resource"}

    response = await server._handle_message(client_id, message)
    assert response == {"status": "subscribed"}
    assert client_id in server.manager.subscriptions["test-resource"]


@pytest.mark.asyncio
async def test_handle_message_unsubscribe(
    server: NovaWebSocketServer, mock_handler: MockResourceHandler
) -> None:
    """Test message handling for unsubscribe action."""
    client_id = "test-client"
    resource_id = "test-resource"

    # Subscribe first
    server.manager.subscribe(client_id, resource_id)

    message = {"action": "unsubscribe", "resource_id": resource_id}

    response = await server._handle_message(client_id, message)
    assert response == {"status": "unsubscribed"}
    assert resource_id not in server.manager.subscriptions


@pytest.mark.asyncio
async def test_handle_message_get_metadata(
    server: NovaWebSocketServer, mock_handler: MockResourceHandler
) -> None:
    """Test message handling for get_metadata action."""
    client_id = "test-client"
    message = {"action": "get_metadata", "resource_id": "test-resource"}

    response = await server._handle_message(client_id, message)
    assert response == {"metadata": mock_handler.get_metadata()}


@pytest.mark.asyncio
async def test_handle_message_invalid(server: NovaWebSocketServer) -> None:
    """Test message handling for invalid messages."""
    client_id = "test-client"

    # Test missing action
    with pytest.raises(ResourceError) as exc:
        await server._handle_message(client_id, {"resource_id": "test"})
    assert "Missing action" in str(exc.value)

    # Test missing resource_id
    with pytest.raises(ResourceError) as exc:
        await server._handle_message(client_id, {"action": "test"})
    assert "Missing action" in str(exc.value)

    # Test unknown resource
    with pytest.raises(ResourceError) as exc:
        await server._handle_message(
            client_id, {"action": "subscribe", "resource_id": "unknown"}
        )
    assert "Unknown resource" in str(exc.value)

    # Test unknown action
    with pytest.raises(ResourceError) as exc:
        await server._handle_message(
            client_id, {"action": "unknown", "resource_id": "test-resource"}
        )
    assert "Unknown action" in str(exc.value)


@pytest.mark.asyncio
async def test_notify_resource_change(
    server: NovaWebSocketServer, mock_handler: MockResourceHandler
) -> None:
    """Test resource change notification."""
    client_id = "test-client"
    resource_id = "test-resource"

    # Create mock WebSocket
    websocket = Mock(spec=WebSocket)
    websocket.send_json = Mock()

    # Connect and subscribe
    await server.manager.connect(websocket, client_id)
    server.manager.subscribe(client_id, resource_id)

    # Trigger change
    await server._notify_resource_change(resource_id)

    # Verify notification sent
    websocket.send_json.assert_called_once()
    args = websocket.send_json.call_args[0][0]
    assert args["type"] == "change"
    assert args["resource_id"] == resource_id
    assert args["metadata"] == mock_handler.get_metadata()
