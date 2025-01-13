"""Unit tests for notification system."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from pydantic import HttpUrl, ValidationError

from nova.server.protocol.notifications import (
    NotificationEvent,
    NotificationManager,
    WebhookConfig,
)

if TYPE_CHECKING:
    pass


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, status: int = 200) -> None:
        """Initialize mock response."""
        self.status = status

    async def __aenter__(self) -> MockResponse:
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
        self.close = AsyncMock()  # Use AsyncMock for async close method


@pytest_asyncio.fixture
async def async_manager() -> AsyncGenerator[NotificationManager, None]:
    """Create and start notification manager.

    Returns:
        AsyncGenerator yielding NotificationManager instance
    """
    manager = NotificationManager()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def webhook_config() -> WebhookConfig:
    """Create webhook configuration.

    Returns:
        WebhookConfig instance
    """
    return WebhookConfig(
        url=HttpUrl("http://test.com/webhook"),
        secret="test-secret",
        events=["test.event"],
        retry_count=2,
        retry_delay=1,
    )


@pytest.fixture
def notification_event() -> NotificationEvent:
    """Create notification event.

    Returns:
        NotificationEvent instance
    """
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
async def test_notify_success(
    async_manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test successful notification delivery."""
    # Setup mock session
    session = MockClientSession()
    session.post.return_value = MockResponse(200)
    async_manager._http_session = cast(ClientSession | None, session)

    # Register webhook and send notification
    async_manager.register_webhook(webhook_config)
    await async_manager.notify(notification_event)

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
            webhook_config.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert headers["X-Nova-Signature"] == expected_signature


@pytest.mark.asyncio
async def test_notify_retry(
    async_manager: NotificationManager,
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
    async_manager._http_session = cast(ClientSession | None, session)

    # Register webhook and send notification
    async_manager.register_webhook(webhook_config)
    await async_manager.notify(notification_event)

    # Verify retry
    assert session.post.call_count == 2


@pytest.mark.asyncio
async def test_notify_failure(
    async_manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test notification failure."""
    # Setup mock session with all failures
    session = MockClientSession()
    session.post.return_value = MockResponse(500)
    async_manager._http_session = cast(ClientSession | None, session)

    # Register webhook and send notification
    async_manager.register_webhook(webhook_config)
    await async_manager.notify(notification_event)

    # Verify all retries attempted
    assert session.post.call_count == webhook_config.retry_count


@pytest.mark.asyncio
async def test_notify_no_session(
    async_manager: NotificationManager,
    notification_event: NotificationEvent,
) -> None:
    """Test notification without session."""
    async_manager._http_session = None
    # Attempt notification without session
    await async_manager.notify(notification_event)
    # Should not raise exception


@pytest.mark.asyncio
async def test_notify_no_subscribers(
    async_manager: NotificationManager,
    notification_event: NotificationEvent,
) -> None:
    """Test notification with no subscribers."""
    # Setup mock session
    session = MockClientSession()
    async_manager._http_session = cast(ClientSession | None, session)

    # Send notification without subscribers
    await async_manager.notify(notification_event)

    # Verify no webhook calls
    session.post.assert_not_called()


def test_generate_signature(
    async_manager: NotificationManager,
    webhook_config: WebhookConfig,
    notification_event: NotificationEvent,
) -> None:
    """Test signature generation."""
    payload = json.dumps(notification_event)
    if webhook_config.secret:
        signature = async_manager._generate_signature(webhook_config.secret, payload)

        # Verify signature
        expected_signature = hmac.new(
            webhook_config.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert signature == expected_signature
