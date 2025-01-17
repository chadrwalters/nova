"""Test monitor command."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nova.cli.commands.monitor import MonitorCommand
from nova.monitoring.logs import LogManager
from nova.vector_store.store import VectorStore


@pytest.fixture
def mock_vector_store(tmp_path: Path) -> MagicMock:
    """Create a mock vector store."""
    mock = MagicMock(spec=VectorStore)
    # Create a mock stats object with the required attributes
    stats_mock = MagicMock()
    stats_mock.get_stats.return_value = {
        "total_documents": 100,
        "total_chunks": 100,
        "total_embeddings": 100,
        "total_searches": 50,
        "cache_hits": 30,
        "cache_misses": 20,
        "avg_chunk_size": 256.5,
        "last_update": "2024-03-15 10:00:00",
    }
    # Attach the stats mock to the vector store mock
    mock.stats = stats_mock

    # Create a mock collection with required methods
    collection_mock = MagicMock()
    collection_mock.get.return_value = {"ids": list(range(100))}
    mock.collection = collection_mock

    return mock


@pytest.fixture
def mock_log_manager(tmp_path: Path) -> MagicMock:
    """Create a mock log manager."""
    mock = MagicMock(spec=LogManager)
    mock.get_stats.return_value = {
        "total_files": 3,
        "total_entries": 100,
        "error_entries": 5,
        "warning_entries": 10,
        "info_entries": 85,
    }
    return mock


@pytest.fixture
def monitor_command(mock_vector_store: MagicMock, mock_log_manager: MagicMock) -> MonitorCommand:
    """Create a monitor command with mocked dependencies."""
    command = MonitorCommand()
    command.vector_store = mock_vector_store
    command.log_manager = mock_log_manager
    command.vector_stats = mock_vector_store.stats  # Use the stats from the mock vector store
    return command


def test_monitor_health(
    monitor_command: MonitorCommand, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test health check command."""
    # Create required directories for health check
    nova_dir = tmp_path / ".nova"
    vectors_dir = nova_dir / "vectors"
    vectors_dir.mkdir(parents=True, exist_ok=True)
    (vectors_dir / "chroma").mkdir(parents=True, exist_ok=True)
    (nova_dir / "cache").mkdir(parents=True, exist_ok=True)
    (nova_dir / "logs").mkdir(parents=True, exist_ok=True)

    # Change to the temporary directory for the test
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        monitor_command.run(subcommand="health")

    captured = capsys.readouterr()

    # Verify directory checks
    assert "Vector store directory exists" in captured.out
    assert "ChromaDB directory exists" in captured.out
    assert "Cache directory exists" in captured.out
    assert "Logs directory exists" in captured.out
    assert "ChromaDB collection is accessible" in captured.out


def test_monitor_stats(monitor_command: MonitorCommand, capsys: pytest.CaptureFixture[str]) -> None:
    """Test stats command."""
    monitor_command.run(subcommand="stats")
    captured = capsys.readouterr()

    # Verify vector store stats output
    assert "Vector Store Statistics:" in captured.out
    assert "Documents in collection: 100" in captured.out
    assert "Total documents processed: 100" in captured.out
    assert "Total chunks: 100" in captured.out
    assert "Total embeddings: 100" in captured.out
    assert "Total searches: 50" in captured.out
    assert "Cache hits: 30" in captured.out
    assert "Cache misses: 20" in captured.out
    assert "Last update: 2024-03-15 10:00:00" in captured.out

    # Verify log stats output
    assert "Log Statistics:" in captured.out
    assert "Total log files: 3" in captured.out
    assert "Total entries: 100" in captured.out
    assert "Error entries: 5" in captured.out
    assert "Warning entries: 10" in captured.out
    assert "Info entries: 85" in captured.out


def test_monitor_logs(monitor_command: MonitorCommand, capsys: pytest.CaptureFixture[str]) -> None:
    """Test logs command."""
    # Setup mock log entries
    mock_entries = [
        {"timestamp": "2024-03-15 10:00:00", "level": "INFO", "message": "Test info message"},
        {"timestamp": "2024-03-15 10:01:00", "level": "WARNING", "message": "Test warning message"},
        {"timestamp": "2024-03-15 10:02:00", "level": "ERROR", "message": "Test error message"},
    ]
    monitor_command.log_manager.tail_logs.return_value = mock_entries

    monitor_command.run(subcommand="logs")
    captured = capsys.readouterr()

    # Verify log entries output
    assert "Recent Log Entries:" in captured.out
    for entry in mock_entries:
        assert entry["timestamp"] in captured.out
        assert entry["level"] in captured.out
        assert entry["message"] in captured.out


def test_monitor_missing_args(monitor_command: MonitorCommand) -> None:
    """Test monitor command with missing arguments."""
    with pytest.raises(
        TypeError,
        match="MonitorCommand.run\\(\\) missing 1 required positional argument: 'subcommand'",
    ):
        monitor_command.run()  # type: ignore


def test_monitor_invalid_subcommand(monitor_command: MonitorCommand) -> None:
    """Test monitor command with invalid subcommand."""
    with pytest.raises(ValueError, match="Invalid subcommand: invalid"):
        monitor_command.run(subcommand="invalid")


def test_monitor_health_missing_dirs(
    monitor_command: MonitorCommand, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test health check with missing directories."""
    # Change to the temporary directory for the test
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        monitor_command.run(subcommand="health")

    captured = capsys.readouterr()

    # Verify missing directory messages
    assert "Vector store directory does not exist" in captured.out
    assert "ChromaDB directory does not exist" in captured.out
    assert "Cache directory does not exist" in captured.out
    assert "Logs directory does not exist" in captured.out
