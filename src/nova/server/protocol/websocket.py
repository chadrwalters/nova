"""WebSocket server implementation for Nova MCP."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader
from starlette.middleware.cors import CORSMiddleware

from nova.server.types import ResourceError, ResourceHandler

# Configure logging
logger = logging.getLogger(__name__)

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


class WebSocketManager:
    """WebSocket connection manager."""

    def __init__(self) -> None:
        """Initialize WebSocket manager."""
        self.active_connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # resource_id -> set of client_ids
        self._rate_limits: dict[
            str, list[datetime]
        ] = {}  # client_id -> list of timestamps
        self.MAX_REQUESTS_PER_MINUTE = 60

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Connect new WebSocket client.

        Args:
            websocket: WebSocket connection
            client_id: Client identifier
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self._rate_limits[client_id] = []
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str) -> None:
        """Disconnect WebSocket client.

        Args:
            client_id: Client identifier
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self._rate_limits[client_id]
            # Remove client from all subscriptions
            for subs in self.subscriptions.values():
                subs.discard(client_id)
            logger.info(f"Client {client_id} disconnected")

    def subscribe(self, client_id: str, resource_id: str) -> None:
        """Subscribe client to resource changes.

        Args:
            client_id: Client identifier
            resource_id: Resource identifier
        """
        if resource_id not in self.subscriptions:
            self.subscriptions[resource_id] = set()
        self.subscriptions[resource_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to {resource_id}")

    def unsubscribe(self, client_id: str, resource_id: str) -> None:
        """Unsubscribe client from resource changes.

        Args:
            client_id: Client identifier
            resource_id: Resource identifier
        """
        if resource_id in self.subscriptions:
            self.subscriptions[resource_id].discard(client_id)
            if not self.subscriptions[resource_id]:
                del self.subscriptions[resource_id]
            logger.info(f"Client {client_id} unsubscribed from {resource_id}")

    async def broadcast(self, resource_id: str, message: dict[str, Any]) -> None:
        """Broadcast message to subscribed clients.

        Args:
            resource_id: Resource identifier
            message: Message to broadcast
        """
        if resource_id in self.subscriptions:
            for client_id in list(self.subscriptions[resource_id]):
                try:
                    websocket = self.active_connections.get(client_id)
                    if websocket:
                        await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {e}")
                    self.disconnect(client_id)

    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit.

        Args:
            client_id: Client identifier

        Returns:
            True if within rate limit, False otherwise
        """
        now = datetime.now()
        timestamps = self._rate_limits.get(client_id, [])

        # Remove timestamps older than 1 minute
        timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < 60]
        self._rate_limits[client_id] = timestamps

        # Check rate limit
        if len(timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            return False

        # Add new timestamp
        timestamps.append(now)
        return True


class NovaWebSocketServer:
    """Nova WebSocket server implementation."""

    def __init__(
        self,
        api_key: str,
        resources: dict[str, ResourceHandler],
        cors_origins: list[str] | None = None,
    ) -> None:
        """Initialize WebSocket server.

        Args:
            api_key: API key for authentication
            resources: Dictionary of resource handlers
            cors_origins: List of allowed CORS origins
        """
        self.api_key = api_key
        self.resources = resources
        self.manager = WebSocketManager()
        self.app = FastAPI(title="Nova WebSocket Server")

        # Add CORS middleware
        if cors_origins:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Register routes
        self._setup_routes()

        # Register change callbacks
        for resource_id, handler in self.resources.items():

            def create_change_callback(rid: str) -> Callable[[], None]:
                def change_callback() -> None:
                    asyncio.create_task(self._notify_resource_change(rid))

                return change_callback

            handler.on_change(create_change_callback(resource_id))

    def _setup_routes(self) -> None:
        """Set up FastAPI routes."""

        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
            """WebSocket endpoint.

            Args:
                websocket: WebSocket connection
                client_id: Client identifier
            """
            try:
                # Verify API key
                if websocket.headers.get("x-api-key") != self.api_key:
                    await websocket.close(code=4001, reason="Invalid API key")
                    return

                await self.manager.connect(websocket, client_id)

                try:
                    while True:
                        # Receive message
                        message = await websocket.receive_json()

                        # Check rate limit
                        if not self.manager.check_rate_limit(client_id):
                            await websocket.send_json({"error": "Rate limit exceeded"})
                            continue

                        # Handle message
                        try:
                            response = await self._handle_message(client_id, message)
                            if response:
                                await websocket.send_json(response)
                        except ResourceError as e:
                            await websocket.send_json({"error": str(e)})
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            await websocket.send_json(
                                {"error": "Internal server error"}
                            )

                except WebSocketDisconnect:
                    self.manager.disconnect(client_id)

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await websocket.close(code=4000, reason="Internal server error")
                except Exception:  # noqa: BAN-B110
                    # We're already in an error handler, nothing more we can do
                    # If closing the websocket fails, we can't report it anywhere
                    pass

        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            """Health check endpoint.

            Returns:
                Health status
            """
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    async def _handle_message(
        self, client_id: str, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle incoming websocket message.

        Args:
            client_id: Client identifier
            message: Message to handle

        Returns:
            Optional response message

        Raises:
            ResourceError: If resource operation fails
        """
        action = message.get("action")
        resource_id = message.get("resource_id")
        # Note: data field is reserved for future use
        _ = message.get("data", {})

        if not action or not resource_id:
            raise ResourceError("Missing action or resource_id")

        if resource_id not in self.resources:
            raise ResourceError(f"Unknown resource: {resource_id}")

        handler = self.resources[resource_id]

        if action == "subscribe":
            self.manager.subscribe(client_id, resource_id)
            return {"status": "subscribed"}

        elif action == "unsubscribe":
            self.manager.unsubscribe(client_id, resource_id)
            return {"status": "unsubscribed"}

        elif action == "get_metadata":
            if not handler.validate_access("read"):
                raise ResourceError("Read access denied")
            return {"metadata": handler.get_metadata()}

        else:
            raise ResourceError(f"Unknown action: {action}")

    async def _notify_resource_change(self, resource_id: str) -> None:
        """Notify clients of resource change.

        Args:
            resource_id: Resource identifier
        """
        try:
            handler = self.resources[resource_id]
            metadata = handler.get_metadata()
            await self.manager.broadcast(
                resource_id,
                {"type": "change", "resource_id": resource_id, "metadata": metadata},
            )
        except Exception as e:
            logger.error(f"Error notifying resource change: {e}")
