"""Tests for monitor command."""

from pathlib import Path
from collections.abc import Generator

import pytest

from nova.cli.commands.monitor import MonitorCommand


@pytest.fixture
def system_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary system directory."""
    nova_dir = tmp_path / ".nova"
    nova_dir.mkdir()
    (nova_dir / "vectorstore").mkdir()
    (nova_dir / "logs").mkdir()
    yield tmp_path


def test_monitor_health(system_dir: Path) -> None:
    """Test health check command."""
    command = MonitorCommand()
    command.run(subcommand="health", system_dir=str(system_dir))

    # Check that directories exist
    assert (system_dir / ".nova").exists()
    assert (system_dir / ".nova/vectorstore").exists()
    assert (system_dir / ".nova/logs").exists()


def test_monitor_stats(system_dir: Path) -> None:
    """Test stats command."""
    command = MonitorCommand()
    command.run(subcommand="stats", system_dir=str(system_dir))

    # Check that directories exist
    assert (system_dir / ".nova").exists()
    assert (system_dir / ".nova/vectorstore").exists()
    assert (system_dir / ".nova/logs").exists()


def test_monitor_logs(system_dir: Path) -> None:
    """Test logs command."""
    command = MonitorCommand()
    command.run(subcommand="logs", system_dir=str(system_dir))

    # Check that directories exist
    assert (system_dir / ".nova").exists()
    assert (system_dir / ".nova/vectorstore").exists()
    assert (system_dir / ".nova/logs").exists()


def test_monitor_missing_args() -> None:
    """Test monitor command with missing arguments."""
    command = MonitorCommand()
    with pytest.raises(KeyError, match="No subcommand provided"):
        command.run()
