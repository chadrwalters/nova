import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from rich.progress import Progress, Task
from rich.table import Table

from nova.core.console.logger import ConsoleLogger
from nova.core.console.phase_runner import PhaseStats
from nova.core.console.pipeline_reporter import PipelineReporter, PipelineStats


@pytest.fixture
def mock_progress():
    """Create a mock Progress instance."""
    progress = MagicMock(spec=Progress)
    task = MagicMock(spec=Task)
    task.id = "test_task"
    progress.add_task.return_value = task
    return progress


@pytest.fixture
def pipeline_reporter(mock_progress):
    """Create a PipelineReporter instance for testing."""
    with patch('nova.core.console.logger.ConsoleLogger.progress', return_value=mock_progress):
        reporter = PipelineReporter()
        yield reporter


def test_pipeline_stats():
    """Test PipelineStats calculations."""
    stats = PipelineStats(total_files=20)
    
    # Test initial state
    assert stats.files_processed == 0
    assert stats.files_skipped == 0
    assert stats.files_failed == 0
    assert stats.files_remaining == 20
    assert stats.success_rate == 0.0
    assert not stats.file_types
    assert not stats.phase_stats
    
    # Test with some processed files
    stats.files_processed = 10
    stats.files_skipped = 5
    stats.files_failed = 2
    stats.file_types.update({".md", ".txt"})
    
    assert stats.files_remaining == 3
    assert stats.success_rate == 50.0
    assert stats.file_types == {".md", ".txt"}
    
    # Test duration calculation
    stats.start_time = datetime.now() - timedelta(seconds=10)
    stats.end_time = datetime.now()
    assert 9.5 <= stats.duration <= 10.5  # Allow for small timing differences


def test_pipeline_reporter_start_pipeline(pipeline_reporter, mock_progress):
    """Test starting the pipeline."""
    with patch.object(pipeline_reporter.logger, 'info') as mock_info:
        pipeline_reporter.start_pipeline(20)
        
        assert pipeline_reporter.stats.total_files == 20
        assert pipeline_reporter._progress is not None
        assert pipeline_reporter._task is not None
        
        mock_info.assert_any_call("Starting pipeline processing")
        mock_info.assert_any_call("Total files to process: 20")
        mock_progress.start.assert_called_once()


def test_pipeline_reporter_update_progress(pipeline_reporter, mock_progress):
    """Test updating pipeline progress."""
    pipeline_reporter.start_pipeline(20)
    
    pipeline_reporter.update_progress(
        files_processed=10,
        files_skipped=5,
        files_failed=2,
        file_types={".md", ".txt"}
    )
    
    stats = pipeline_reporter.stats
    assert stats.files_processed == 10
    assert stats.files_skipped == 5
    assert stats.files_failed == 2
    assert stats.files_remaining == 3
    assert stats.file_types == {".md", ".txt"}
    
    mock_progress.update.assert_called_once_with(
        "test_task",
        completed=17,
        description="Processed: 10, Skipped: 5, Failed: 2, Remaining: 3"
    )


def test_pipeline_reporter_add_phase_stats(pipeline_reporter):
    """Test adding phase statistics."""
    phase1_stats = PhaseStats(
        phase_name="phase1",
        total_files=10,
        files_processed=8,
        files_skipped=1,
        files_failed=1
    )
    
    phase2_stats = PhaseStats(
        phase_name="phase2",
        total_files=5,
        files_processed=4,
        files_failed=1
    )
    
    pipeline_reporter.add_phase_stats(phase1_stats)
    pipeline_reporter.add_phase_stats(phase2_stats)
    
    assert len(pipeline_reporter.stats.phase_stats) == 2
    assert pipeline_reporter.get_phase_stats("phase1") == phase1_stats
    assert pipeline_reporter.get_phase_stats("phase2") == phase2_stats


def test_pipeline_reporter_end_pipeline(pipeline_reporter, mock_progress):
    """Test ending the pipeline."""
    pipeline_reporter.start_pipeline(20)
    pipeline_reporter.update_progress(
        files_processed=15,
        files_skipped=3,
        files_failed=2,
        file_types={".md", ".txt"}
    )
    
    # Add some phase stats
    phase_stats = PhaseStats(
        phase_name="test_phase",
        total_files=20,
        files_processed=15,
        files_skipped=3,
        files_failed=2
    )
    pipeline_reporter.add_phase_stats(phase_stats)
    
    with patch.object(pipeline_reporter.logger, 'info') as mock_info:
        with patch.object(pipeline_reporter.logger.console, 'print') as mock_print:
            pipeline_reporter.end_pipeline()
            
            assert pipeline_reporter._progress is None
            assert pipeline_reporter._task is None
            assert pipeline_reporter.stats.end_time is not None
            
            mock_info.assert_any_call("Pipeline processing complete")
            mock_progress.stop.assert_called_once()
            
            # Verify that both summary tables were printed
            assert len(mock_print.call_args_list) >= 2
            assert all(isinstance(call[0][0], Table) for call in mock_print.call_args_list)


def test_pipeline_reporter_get_stats(pipeline_reporter):
    """Test getting phase statistics."""
    phase1_stats = PhaseStats(phase_name="phase1", total_files=10)
    phase2_stats = PhaseStats(phase_name="phase2", total_files=20)
    
    pipeline_reporter.add_phase_stats(phase1_stats)
    pipeline_reporter.add_phase_stats(phase2_stats)
    
    # Test get_phase_stats
    assert pipeline_reporter.get_phase_stats("phase1") == phase1_stats
    assert pipeline_reporter.get_phase_stats("nonexistent") is None
    
    # Test get_all_phase_stats
    all_stats = pipeline_reporter.get_all_phase_stats()
    assert len(all_stats) == 2
    assert all_stats == [phase1_stats, phase2_stats]


def test_pipeline_reporter_empty_pipeline(pipeline_reporter):
    """Test pipeline with no files or phases."""
    pipeline_reporter.start_pipeline(0)
    
    with patch.object(pipeline_reporter.logger, 'info'):
        with patch.object(pipeline_reporter.logger.console, 'print') as mock_print:
            pipeline_reporter.end_pipeline()
            
            # Verify that at least the main summary table was printed
            assert mock_print.called
            assert any(
                isinstance(call[0][0], Table) and call[0][0].title == "Pipeline Summary"
                for call in mock_print.call_args_list
            ) 