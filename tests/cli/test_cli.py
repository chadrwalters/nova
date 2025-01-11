"""Test suite for Nova CLI functionality."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import nest_asyncio
import pytest
from click.testing import CliRunner

from nova.cli import cli

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_config(tmp_path: Path) -> Path:
    """Create a test config file."""
    config_path = tmp_path / "test_nova.yaml"
    config_path.write_text("""
base_dir: data
cache_dir: cache
api:
  openai_api_key: test_key
  vision_prompt: "Describe this image:"
security:
  auth_token: test-token
  enable_tls: false
monitoring:
  enabled: true
  log_path: test.log
  metrics:
    port: 8000
    host: localhost
  alerting:
    log_path: alerts.log
    email_config:
      smtp_server: smtp.test.com
      smtp_port: 587
      username: test@test.com
      password: test_password
      from_addr: alerts@test.com
      to_addrs:
        - admin@test.com
    slack_webhook: https://hooks.slack.com/services/test
cloud:
  provider: aws
  region: us-west-2
  instance_type: t3.medium
handlers:
  image_formats:
    - png
    - jpg
    - jpeg
    - gif
""")
    return config_path


@pytest.fixture
def test_env() -> None:
    """Set up test environment variables."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
        yield


@pytest.fixture
def mock_query_context():
    """Mock query processing context."""
    async def mock_process_query(*args, **kwargs):
        return "Test response"

    with patch("nova.cli.process_query", new=AsyncMock(side_effect=mock_process_query)):
        yield


@pytest.fixture
def mock_stream_context():
    """Mock streaming query context."""
    async def mock_process_query_stream(*args, **kwargs):
        for chunk in ["Test", " response"]:
            yield chunk

    with patch("nova.cli.process_query_stream", new=AsyncMock(side_effect=mock_process_query_stream)):
        yield


@pytest.mark.asyncio
async def test_cli_process_query(
    runner: CliRunner,
    test_config: Path,
    test_env: None,
    mock_query_context: None
) -> None:
    """Test query processing command."""
    result = runner.invoke(cli, ["query", "--config", str(test_config), "test query"])
    print(f"\nCommand output:\n{result.output}")
    assert result.exit_code == 0
    assert "Test response" in result.output


@pytest.mark.asyncio
async def test_cli_process_export(
    runner: CliRunner,
    test_config: Path,
    test_env: None,
    mock_query_context: None,
    tmp_path: Path
) -> None:
    """Test export command."""
    export_path = tmp_path / "export"
    export_path.mkdir(parents=True, exist_ok=True)
    assets_path = export_path / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)
    test_note = export_path / "test.md"
    test_note.write_text("# Test Note\nThis is a test note.")

    result = runner.invoke(
        cli,
        ["process-export", "--config", str(test_config), str(export_path)]
    )
    print(f"\nCommand output:\n{result.output}")
    assert result.exit_code == 0
    assert "Processed 1 notes from" in result.output


@pytest.mark.asyncio
async def test_cli_streaming_query(
    runner: CliRunner,
    test_config: Path,
    test_env: None,
    mock_stream_context: None
) -> None:
    """Test streaming query command."""
    result = runner.invoke(
        cli,
        ["query", "--config", str(test_config), "--stream", "test query"]
    )
    print(f"\nCommand output:\n{result.output}")
    assert result.exit_code == 0
    assert "Test response" in result.output


@pytest.mark.asyncio
async def test_cli_help(
    runner: CliRunner,
    test_env: None
) -> None:
    """Test help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Nova" in result.output 