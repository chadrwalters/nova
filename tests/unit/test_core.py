"""
Unit tests for Nova core functionality.
"""
import asyncio
import json
import logging
from pathlib import Path

import pytest

from nova.config.settings import LoggingConfig
from nova.core.logging import NovaFormatter, NovaLogger
from nova.core.metadata import FileMetadata
from nova.core.metrics import MetricsTracker, OperationMetrics, timing


@pytest.mark.unit
@pytest.mark.core
class TestMetricsTracker:
    """Test the metrics tracking functionality."""

    @pytest.mark.asyncio
    async def test_record_operation_duration(self):
        """Test recording operation duration."""
        tracker = MetricsTracker()

        # Record an operation
        await tracker.record_operation("test_op", 0.1)

        metrics = tracker.get_metrics_summary()
        assert "test_op" in metrics
        assert metrics["test_op"]["call_count"] == 1
        assert metrics["test_op"]["total_time"] > 0

    @pytest.mark.asyncio
    async def test_update_time_statistics(self):
        """Test updating time statistics."""
        tracker = MetricsTracker()

        # Record multiple operations
        durations = [0.1, 0.2, 0.3]
        for duration in durations:
            await tracker.record_operation("test_op", duration)

        metrics = tracker.get_metrics_summary()
        assert metrics["test_op"]["call_count"] == 3
        assert metrics["test_op"]["total_time"] == sum(durations)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test handling concurrent operations."""
        tracker = MetricsTracker()

        # Start outer operation
        await tracker.record_operation("outer", 0.2)
        await tracker.record_operation("inner", 0.1)

        metrics = tracker.get_metrics_summary()
        assert "outer" in metrics
        assert "inner" in metrics
        assert metrics["outer"]["call_count"] == 1
        assert metrics["inner"]["call_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_summary(self):
        """Test getting metrics summary."""
        tracker = MetricsTracker()

        # Record some operations
        operations = ["op1", "op2", "op3"]
        for op in operations:
            await tracker.record_operation(op, 0.1)

        summary = tracker.get_metrics_summary()
        assert all(op in summary for op in operations)
        assert all(isinstance(summary[op], dict) for op in operations)
        assert all("call_count" in summary[op] for op in operations)
        assert all("total_time" in summary[op] for op in operations)

    @pytest.mark.asyncio
    async def test_timing_context_manager(self):
        """Test timing context manager."""
        tracker = MetricsTracker()

        # Use context manager
        async with timing("test_op", tracker):
            await asyncio.sleep(0.1)

        metrics = tracker.get_metrics_summary()
        assert "test_op" in metrics
        assert metrics["test_op"]["call_count"] == 1
        assert metrics["test_op"]["total_time"] > 0


@pytest.mark.unit
@pytest.mark.core
class TestFileMetadata:
    """Test file metadata functionality."""

    def test_save_metadata(self, mock_fs):
        """Test saving metadata to file."""
        file_path = mock_fs["input"] / "test.txt"
        file_path.touch()

        metadata = FileMetadata(file_path)
        metadata.metadata["test_key"] = "test_value"
        metadata.save(mock_fs["output"] / "test.metadata.json")

        # Verify file exists and content
        metadata_path = mock_fs["output"] / "test.metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            saved_data = json.load(f)
            assert saved_data["file_path"] == str(file_path)
            assert saved_data["metadata"]["test_key"] == "test_value"
            assert not saved_data["processed"]
            assert not saved_data["has_errors"]

    def test_load_metadata(self, mock_fs):
        """Test loading metadata from file."""
        file_path = mock_fs["input"] / "test.txt"
        file_path.touch()

        # Create metadata file
        metadata_path = mock_fs["output"] / "test.metadata.json"
        metadata_content = {
            "file_path": str(file_path),
            "processed": True,
            "unchanged": False,
            "reprocessed": False,
            "output_files": [],
            "errors": {},
            "metadata": {"test_key": "test_value"},
            "title": "test",
            "has_errors": False,
            "links": [],
            "handler_name": "test_handler",
            "handler_version": "1.0",
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata_content, f)

        # Create metadata and verify
        metadata = FileMetadata.from_file(file_path, "test_handler", "1.0")
        assert metadata.file_path == file_path
        assert metadata.metadata["handler_name"] == "test_handler"
        assert metadata.metadata["handler_version"] == "1.0"


@pytest.mark.unit
@pytest.mark.core
class TestNovaLogger:
    """Test Nova logger functionality."""

    def test_logger_configuration(self):
        """Test logger configuration."""
        config = LoggingConfig(
            level="DEBUG",
            console_level="DEBUG",
            format="%(asctime)s [%(levelname)s] %(message)s",
            date_format="%Y-%m-%d %H:%M:%S",
            handlers=["console"],
        )

        # Register NovaLogger as the logger class
        logging.setLoggerClass(NovaLogger)

        formatter = NovaFormatter(config)
        logger = logging.getLogger("nova.test")

        # Remove any existing handlers
        logger.handlers = []

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.setLevel(logging.DEBUG)
        logger.debug("Test message")

        assert isinstance(logger, NovaLogger)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, NovaFormatter)

    def test_log_levels(self):
        """Test different logging levels."""
        config = LoggingConfig(
            level="DEBUG",
            console_level="DEBUG",
            format="%(asctime)s [%(levelname)s] %(message)s",
            date_format="%Y-%m-%d %H:%M:%S",
            handlers=["console"],
        )

        # Register NovaLogger as the logger class
        logging.setLoggerClass(NovaLogger)

        formatter = NovaFormatter(config)
        logger = logging.getLogger("nova.test")

        # Remove any existing handlers
        logger.handlers = []

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.setLevel(logging.DEBUG)
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        assert isinstance(logger, NovaLogger)
        assert len(logger.handlers) == 1
