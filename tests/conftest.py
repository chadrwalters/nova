"""Test configuration and fixtures."""

pytest_plugins = ["pytest_asyncio"]

# Remove custom event_loop fixture to use pytest-asyncio's built-in one 