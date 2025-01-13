"""Change notification system implementation."""

import asyncio
import json
import logging
from typing import Any, TypedDict
from uuid import uuid4

import aiohttp
from pydantic import BaseModel, Field, HttpUrl

# Configure logging
logger = logging.getLogger(__name__)


class WebhookConfig(BaseModel):
    """Webhook configuration."""

    url: HttpUrl = Field(..., description="Webhook URL")
    secret: str | None = Field(None, description="Webhook secret for authentication")
    events: list[str] = Field(
        default_factory=list, description="List of event types to receive"
    )
    retry_count: int = Field(default=3, ge=1, description="Number of retry attempts")
    retry_delay: int = Field(
        default=5, ge=1, description="Delay between retries in seconds"
    )


class NotificationEvent(TypedDict):
    """Notification event type."""

    id: str
    type: str
    resource_id: str
    timestamp: float
    data: dict[str, Any]


class NotificationManager:
    """Change notification manager."""

    def __init__(self) -> None:
        """Initialize notification manager."""
        self._webhooks: dict[str, WebhookConfig] = {}
        self._event_subscribers: dict[
            str, set[str]
        ] = {}  # event_type -> set of webhook_ids
        self._http_session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Start notification manager."""
        self._http_session = aiohttp.ClientSession()

    async def stop(self) -> None:
        """Stop notification manager."""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

    def register_webhook(self, config: WebhookConfig) -> str:
        """Register webhook configuration.

        Args:
            config: Webhook configuration

        Returns:
            Webhook identifier
        """
        webhook_id = str(uuid4())
        self._webhooks[webhook_id] = config

        # Register event subscriptions
        for event_type in config.events:
            if event_type not in self._event_subscribers:
                self._event_subscribers[event_type] = set()
            self._event_subscribers[event_type].add(webhook_id)

        logger.info(f"Registered webhook {webhook_id} for events {config.events}")
        return webhook_id

    def unregister_webhook(self, webhook_id: str) -> None:
        """Unregister webhook.

        Args:
            webhook_id: Webhook identifier
        """
        if webhook_id in self._webhooks:
            config = self._webhooks[webhook_id]

            # Remove event subscriptions
            for event_type in config.events:
                if event_type in self._event_subscribers:
                    self._event_subscribers[event_type].discard(webhook_id)
                    if not self._event_subscribers[event_type]:
                        del self._event_subscribers[event_type]

            del self._webhooks[webhook_id]
            logger.info(f"Unregistered webhook {webhook_id}")

    async def notify(self, event: NotificationEvent) -> None:
        """Send notification event.

        Args:
            event: Notification event
        """
        if not self._http_session:
            logger.error("Notification manager not started")
            return

        # Get subscribers for event type
        webhook_ids = self._event_subscribers.get(event["type"], set())

        # Send notifications
        for webhook_id in webhook_ids:
            config = self._webhooks.get(webhook_id)
            if not config:
                continue

            # Send webhook with retries
            for attempt in range(config.retry_count):
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "X-Nova-Event": event["type"],
                        "X-Nova-Timestamp": str(event["timestamp"]),
                    }

                    # Add webhook secret if configured
                    if config.secret:
                        headers["X-Nova-Signature"] = self._generate_signature(
                            config.secret, json.dumps(event)
                        )

                    async with self._http_session.post(
                        str(config.url), json=event, headers=headers
                    ) as response:
                        if response.status < 400:
                            logger.info(
                                f"Webhook {webhook_id} delivered event {event['id']} "
                                f"(attempt {attempt + 1}/{config.retry_count})"
                            )
                            break

                        logger.warning(
                            f"Webhook {webhook_id} failed to deliver event {event['id']} "
                            f"with status {response.status} "
                            f"(attempt {attempt + 1}/{config.retry_count})"
                        )

                except Exception as e:
                    logger.error(
                        f"Error delivering webhook {webhook_id} event {event['id']}: {e} "
                        f"(attempt {attempt + 1}/{config.retry_count})"
                    )

                if attempt < config.retry_count - 1:
                    await asyncio.sleep(config.retry_delay)

    def _generate_signature(self, secret: str, payload: str) -> str:
        """Generate webhook signature.

        Args:
            secret: Webhook secret
            payload: JSON payload

        Returns:
            Signature string
        """
        import hmac
        import hashlib

        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
