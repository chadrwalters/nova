"""Unit tests for notification system."""

import hmac
import hashlib
import json
from datetime import datetime
from typing import Any, cast
import pytest
from unittest.mock import Mock

try:
    from aiohttp import ClientResponse, ClientSession
except ImportError:
    # Mock aiohttp types for type checking
    class ClientResponse:
        pass  # type: ignore

    class ClientSession:
        pass  # type: ignore


from pydantic import HttpUrl, ValidationError

from nova.server.protocol.notifications import (
    NotificationManager,
    WebhookConfig,
    NotificationEvent,
)


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, status: int = 200) -> None:
        """Initialize mock response."""
        self.status = status

    async def __aenter__(self) -> "MockResponse":
        """Enter async context."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        pass


class MockClientSession:
    """Mock aiohttp client session."""

    def __init__(self) -> None:
        """Initialize mock session."""
        self.post = Mock()
        self.close = Mock()


@pytest.fixture
def manager() -> NotificationManager:
    """Create notification manager."""
    return NotificationManager()


@pytest.fixture
def webhook_config() -> WebhookConfig:
    """Create webhook configuration."""
    return WebhookConfig(
        url=HttpUrl("http://test.com/webhook"),
        secret="test-secret",
        events=["test.event"],
        retry_count=2,
        retry_delay=1,
    )


@pytest.fixture
def notification_event() -> NotificationEvent:
    """Create notification event."""
    return {
        "id": "test-id",
        "type": "test.event",
        "resource_id": "test-resource",
        "timestamp": datetime.now().timestamp(),
        "data": {"key": "value"},
    }


def test_webhook_config_validation() -> None:
    """Test webhook configuration validation."""
    # Test valid config with secret
    config = WebhookConfig(url=HttpUrl("http://test.com/webhook"), secret="test-secret")
    assert str(config.url) == "http://test.com/webhook"
    assert config.events == []
    assert config.retry_count == 3
    assert config.retry_delay == 5

    # Test valid config without secret
    config = WebhookConfig(url=HttpUrl("http://test.com/webhook"), secret=None)
    assert str(config.url) == "http://test.com/webhook"
    assert config.secret is None

    # Test invalid URL format
    with pytest.raises(ValidationError):
        # Pass raw string to trigger validation error
        WebhookConfig.model_validate_json('{"url": "not-a-url", "secret": null}')

    # Test invalid retry count
    with pytest.raises(ValidationError):
        WebhookConfig(
            url=HttpUrl("http://test.com/webhook"), secret=None, retry_count=0
        )

    # Test invalid retry delay
    with pytest.raises(ValidationError):
        WebhookConfig(
            url=HttpUrl("http://test.com/webhook"), secret=None, retry_delay=0
        )


@pytest.mark.asyncio
async def test_manager_lifecycle(manager: NotificationManager) -> None:
    """Test manager lifecycle."""
    # Test start
    await manager.start()
    assert manager._http_session is not None

    # Test stop
    await manager.stop()
    assert manager._http_session is None


def test_register_webhook(
    manager: NotificationManager, webhook_config: WebhookConfig
) -> None:
    """Test webhook registration."""
    webhook_id = manager.register_webhook(webhook_config)
    assert webhook_id in manager._webhooks
    assert webhook_config.events[0] in manager._event_subscribers
    assert webhook_id in manager._event_subscribers[webhook_config.events[0]]


def test_unregister_webhook(
    manager: NotificationManager, webhook_config: WebhookConfig
) -> None:
    """Test webhook unregistration."""
    webhook_id = manager.register_webhook(webhook_config)
    manager.unregister_webhook(webhook_id)

    assert webhook_id not in manager._webhooks
    assert not manager._event_subscribers


@pytest.mark.asyncio
async def test_notify_success(
    manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test successful notification delivery."""
    # Setup mock session
    session = MockClientSession()
    session.post.return_value = MockResponse(200)
    manager._http_session = cast(ClientSession, session)

    # Register webhook
    webhook_id = manager.register_webhook(webhook_config)

    # Send notification
    await manager.notify(notification_event)

    # Verify webhook call
    session.post.assert_called_once()
    args = session.post.call_args
    assert str(args[0][0]) == str(webhook_config.url)

    # Verify headers
    headers = args[1]["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Nova-Event"] == notification_event["type"]
    assert headers["X-Nova-Timestamp"] == str(notification_event["timestamp"])

    # Verify signature
    if webhook_config.secret:
        payload = json.dumps(notification_event)
        expected_signature = hmac.new(
            webhook_config.secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        assert headers["X-Nova-Signature"] == expected_signature


@pytest.mark.asyncio
async def test_notify_retry(
    manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test notification retry."""
    # Setup mock session
    session = MockClientSession()
    session.post.side_effect = [
        MockResponse(500),  # First attempt fails
        MockResponse(200),  # Second attempt succeeds
    ]
    manager._http_session = cast(ClientSession, session)

    # Register webhook
    webhook_id = manager.register_webhook(webhook_config)

    # Send notification
    await manager.notify(notification_event)

    # Verify retry
    assert session.post.call_count == 2


@pytest.mark.asyncio
async def test_notify_failure(
    manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test notification failure."""
    # Setup mock session with all failures
    session = MockClientSession()
    session.post.return_value = MockResponse(500)
    manager._http_session = cast(ClientSession, session)

    # Register webhook
    webhook_id = manager.register_webhook(webhook_config)

    # Send notification
    await manager.notify(notification_event)

    # Verify all retries attempted
    assert session.post.call_count == webhook_config.retry_count


@pytest.mark.asyncio
async def test_notify_no_session(
    manager: NotificationManager, notification_event: NotificationEvent
) -> None:
    """Test notification without session."""
    # Attempt notification without starting manager
    await manager.notify(notification_event)
    # Should not raise exception


@pytest.mark.asyncio
async def test_notify_no_subscribers(
    manager: NotificationManager, notification_event: NotificationEvent
) -> None:
    """Test notification with no subscribers."""
    # Start manager
    await manager.start()

    # Send notification for event with no subscribers
    await manager.notify(notification_event)
    # Should not raise exception

    # Cleanup
    await manager.stop()


def test_generate_signature(
    manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test signature generation."""
    payload = json.dumps(notification_event)
    if webhook_config.secret:
        signature = manager._generate_signature(webhook_config.secret, payload)

        # Verify signature
        expected_signature = hmac.new(
            webhook_config.secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        assert signature == expected_signature
