"""Unit tests for Nova core modules."""
import pytest
import json
import logging
from pathlib import Path
from nova.core.metrics import MetricsTracker, OperationMetrics
from nova.core.metadata import FileMetadata
from nova.core.logging import NovaLogger, LoggingManager, NovaLogRecord
from nova.config.settings import LoggingConfig

class TestMetricsTrackerBasics:
    """Tests for the MetricsTracker functionality."""
    
    async def test_record_operation_duration(self):
        """Test that MetricsTracker properly records an operation's duration."""
        tracker = MetricsTracker()
        operation = "test_op"
        duration = 1.5
        
        # Record a single operation
        await tracker.record_operation(operation, duration)
        
        # Verify metrics
        metrics = tracker.operations[operation]
        assert metrics.name == operation
        assert metrics.total_time == duration
        assert metrics.call_count == 1
        assert metrics.min_time == duration
        assert metrics.max_time == duration
        assert metrics.times == [duration]
    
    async def test_update_time_statistics(self):
        """Test that average, min, and max times are updated correctly."""
        tracker = MetricsTracker()
        operation = "test_op"
        durations = [1.0, 0.5, 2.0]  # min=0.5, max=2.0, avg=1.167
        
        # Record multiple operations
        for duration in durations:
            await tracker.record_operation(operation, duration)
        
        # Verify metrics
        metrics = tracker.operations[operation]
        assert metrics.min_time == 0.5
        assert metrics.max_time == 2.0
        assert metrics.total_time == sum(durations)
        assert metrics.call_count == len(durations)
        assert abs(metrics.avg_time - (sum(durations) / len(durations))) < 0.001
        assert metrics.times == durations
    
    async def test_concurrent_operations(self):
        """Test thread safety of operation recording."""
        import asyncio
        
        tracker = MetricsTracker()
        operation = "test_op"
        duration = 1.0
        num_operations = 100
        
        # Create multiple concurrent operation recordings
        tasks = [
            tracker.record_operation(operation, duration)
            for _ in range(num_operations)
        ]
        await asyncio.gather(*tasks)
        
        # Verify metrics
        metrics = tracker.operations[operation]
        assert metrics.call_count == num_operations
        assert metrics.total_time == duration * num_operations
        assert len(metrics.times) == num_operations
    
    async def test_metrics_summary(self):
        """Test getting metrics summary dictionary."""
        tracker = MetricsTracker()
        operations = {
            "op1": [1.0, 2.0],
            "op2": [0.5]
        }
        
        # Record operations
        for op_name, durations in operations.items():
            for duration in durations:
                await tracker.record_operation(op_name, duration)
        
        # Get and verify summary
        summary = tracker.get_metrics_summary()
        
        # Verify op1
        assert "op1" in summary
        op1_metrics = summary["op1"]
        assert op1_metrics["total_time"] == 3.0
        assert op1_metrics["call_count"] == 2
        assert op1_metrics["avg_time"] == 1.5
        assert op1_metrics["min_time"] == 1.0
        assert op1_metrics["max_time"] == 2.0
        assert op1_metrics["times"] == [1.0, 2.0]
        
        # Verify op2
        assert "op2" in summary
        op2_metrics = summary["op2"]
        assert op2_metrics["total_time"] == 0.5
        assert op2_metrics["call_count"] == 1
        assert op2_metrics["avg_time"] == 0.5
        assert op2_metrics["min_time"] == 0.5
        assert op2_metrics["max_time"] == 0.5
        assert op2_metrics["times"] == [0.5]

class TestFileMetadataSaveAndLoad:
    """Tests for FileMetadata save and load operations."""
    
    async def test_save_metadata(self, tmp_path: Path):
        """Test saving FileMetadata with errors and output files."""
        # Create test file path
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        # Create metadata with various fields
        metadata = FileMetadata(file_path)
        metadata.processed = True
        metadata.unchanged = False
        metadata.reprocessed = True
        metadata.add_error("test_handler", "test error")
        metadata.add_output_file(tmp_path / "output.md")
        metadata.title = "Test File"
        metadata.metadata = {
            "key1": "value1",
            "key2": 123
        }
        
        # Save metadata
        metadata_path = tmp_path / "test.metadata.json"
        metadata.save(metadata_path)
        
        # Verify file exists and content
        assert metadata_path.exists()
        with open(metadata_path, 'r') as f:
            saved_data = json.load(f)
        
        # Verify all fields were saved correctly
        assert saved_data["file_path"] == str(file_path)
        assert saved_data["processed"] is True
        assert saved_data["unchanged"] is False
        assert saved_data["reprocessed"] is True
        assert saved_data["errors"] == {"test_handler": "test error"}
        assert saved_data["output_files"] == [str(tmp_path / "output.md")]
        assert saved_data["title"] == "Test File"
        assert saved_data["metadata"] == {"key1": "value1", "key2": 123}
        assert saved_data["has_errors"] is True
    
    async def test_load_metadata_from_file(self, tmp_path: Path):
        """Test loading metadata using from_file factory method."""
        # Create test file
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        # Create metadata using from_file
        metadata = FileMetadata.from_file(
            file_path=file_path,
            handler_name="test_handler",
            handler_version="1.0"
        )
        
        # Verify basic fields
        assert metadata.file_path == file_path
        assert metadata.title == "test"  # from file stem
        assert metadata.processed is False
        assert metadata.unchanged is False
        assert metadata.reprocessed is False
        assert not metadata.errors
        assert not metadata.output_files
        
        # Verify metadata dictionary
        assert metadata.metadata["file_name"] == "test.txt"
        assert metadata.metadata["file_path"] == str(file_path)
        assert metadata.metadata["file_type"] == "txt"
        assert metadata.metadata["handler_name"] == "test_handler"
        assert metadata.metadata["handler_version"] == "1.0"
    
    async def test_metadata_error_handling(self, tmp_path: Path):
        """Test error handling in metadata operations."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        metadata = FileMetadata(file_path)
        
        # Add multiple errors
        metadata.add_error("handler1", "error1")
        metadata.add_error("handler2", "error2")
        
        # Verify error tracking
        assert len(metadata.errors) == 2
        assert metadata.has_errors is True
        assert metadata.errors["handler1"] == "error1"
        assert metadata.errors["handler2"] == "error2"
        
        # Save and verify errors are preserved
        metadata_path = tmp_path / "test.metadata.json"
        metadata.save(metadata_path)
        
        with open(metadata_path, 'r') as f:
            saved_data = json.load(f)
            assert saved_data["errors"] == {
                "handler1": "error1",
                "handler2": "error2"
            }
            assert saved_data["has_errors"] is True
    
    async def test_metadata_output_files(self, tmp_path: Path):
        """Test handling of output files in metadata."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        metadata = FileMetadata(file_path)
        
        # Add output files
        output_files = [
            tmp_path / "output1.md",
            tmp_path / "output2.md",
            tmp_path / "output3.md"
        ]
        for output_file in output_files:
            metadata.add_output_file(output_file)
        
        # Verify output files tracking
        assert len(metadata.output_files) == 3
        for output_file in output_files:
            assert output_file in metadata.output_files
        
        # Save and verify output files are preserved
        metadata_path = tmp_path / "test.metadata.json"
        metadata.save(metadata_path)
        
        with open(metadata_path, 'r') as f:
            saved_data = json.load(f)
            assert saved_data["output_files"] == [str(f) for f in output_files]

class TestNovaLoggerConfiguration:
    """Tests for NovaLogger configuration."""
    
    def test_logger_levels(self, tmp_path: Path):
        """Test that log messages appear at expected levels."""
        # Create test config
        config = LoggingConfig(
            level="INFO",
            file_level="DEBUG",
            console_level="INFO",
            log_dir=tmp_path,
            handlers=["file"],
            phase_levels={
                "parse": "DEBUG",
                "finalize": "WARNING"
            },
            handler_levels={
                "markdown": "DEBUG",
                "document": "WARNING"
            }
        )
        
        # Set up logging
        manager = LoggingManager(config)
        
        # Get loggers for different components
        parse_logger = manager.get_logger("nova.phases.parse")
        finalize_logger = manager.get_logger("nova.phases.finalize")
        markdown_logger = manager.get_logger("nova.handlers.markdown")
        document_logger = manager.get_logger("nova.handlers.document")
        
        # Verify logger levels
        assert parse_logger.getEffectiveLevel() == logging.DEBUG
        assert finalize_logger.getEffectiveLevel() == logging.WARNING
        assert markdown_logger.getEffectiveLevel() == logging.DEBUG
        assert document_logger.getEffectiveLevel() == logging.WARNING
        
        # Verify log file creation
        log_files = list(tmp_path.glob("nova_*.log"))
        assert len(log_files) == 1
    
    def test_handler_configuration(self, tmp_path: Path):
        """Test that file and console handlers are properly configured."""
        # Create test config with both handlers
        config = LoggingConfig(
            level="INFO",
            file_level="DEBUG",
            console_level="INFO",
            log_dir=tmp_path,
            handlers=["console", "file"],
            format="%(asctime)s [%(levelname)s] %(message)s",
            date_format="%Y-%m-%d %H:%M:%S",
            include_context=True
        )
        
        # Set up logging
        manager = LoggingManager(config)
        logger = manager.get_logger("nova.test")
        
        # Verify handlers
        assert len(logger.handlers) == 2
        
        # Get handler types
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RichHandler" in handler_types
        assert "FileHandler" in handler_types
        
        # Test logging with context
        logger.info("Test message", extra={
            "phase": "test_phase",
            "handler": "test_handler",
            "duration": 1.23,
            "file_path": "test.txt"
        })
        
        # Verify log file contains the message with context
        log_files = list(tmp_path.glob("nova_*.log"))
        assert len(log_files) == 1
        
        log_content = log_files[0].read_text()
        assert "Test message" in log_content
        assert "[test_phase]" in log_content
        assert "(test_handler)" in log_content
        assert "(1.23s)" in log_content
        assert "<test.txt>" in log_content
    
    def test_nova_log_record_fields(self):
        """Test that NovaLogRecord properly handles Nova-specific fields."""
        # Create a record
        record = NovaLogRecord(
            name="nova.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Verify default field values
        assert record.phase is None
        assert record.handler is None
        assert record.duration is None
        assert record.context == {}
        assert record.file_path is None
        assert record.progress is None
        
        # Set fields via extra
        extra = {
            "phase": "test_phase",
            "handler": "test_handler",
            "duration": 1.23,
            "context": {"key": "value"},
            "file_path": "test.txt",
            "progress": "50%"
        }
        
        for key, value in extra.items():
            setattr(record, key, value)
        
        # Verify fields were set
        assert record.phase == "test_phase"
        assert record.handler == "test_handler"
        assert record.duration == 1.23
        assert record.context == {"key": "value"}
        assert record.file_path == "test.txt"
        assert record.progress == "50%" 