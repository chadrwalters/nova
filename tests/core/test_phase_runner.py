import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from rich.progress import Progress, Task
from rich.table import Table

from nova.core.console.logger import ConsoleLogger
from nova.core.console.phase_runner import PhaseRunner, PhaseStats


@pytest.fixture
def mock_progress():
    """Create a mock Progress instance."""
    progress = MagicMock(spec=Progress)
    task = MagicMock(spec=Task)
    task.id = "test_task"
    progress.add_task.return_value = task
    return progress


@pytest.fixture
def phase_runner(mock_progress):
    """Create a PhaseRunner instance for testing."""
    with patch('nova.core.console.logger.ConsoleLogger.progress', return_value=mock_progress):
        runner = PhaseRunner()
        yield runner


def test_phase_stats():
    """Test PhaseStats calculations."""
    stats = PhaseStats(
        phase_name="test_phase",
        total_files=10
    )
    
    # Test initial state
    assert stats.files_processed == 0
    assert stats.files_skipped == 0
    assert stats.files_failed == 0
    assert stats.files_remaining == 10
    assert stats.success_rate == 0.0
    
    # Test with some processed files
    stats.files_processed = 5
    stats.files_skipped = 2
    stats.files_failed = 1
    
    assert stats.files_remaining == 2
    assert stats.success_rate == 50.0
    
    # Test duration calculation
    stats.start_time = datetime.now() - timedelta(seconds=10)
    stats.end_time = datetime.now()
    assert 9.5 <= stats.duration <= 10.5  # Allow for small timing differences


def test_phase_runner_start_phase(phase_runner, mock_progress):
    """Test starting a new phase."""
    with patch.object(phase_runner.logger, 'info') as mock_info:
        phase_runner.start_phase("test_phase", 10)
        
        assert phase_runner.current_phase == "test_phase"
        assert "test_phase" in phase_runner.stats
        assert phase_runner.stats["test_phase"].total_files == 10
        
        mock_info.assert_any_call("Starting phase: test_phase")
        mock_info.assert_any_call("Files to process: 10")
        mock_progress.start.assert_called_once()


def test_phase_runner_update_progress(phase_runner, mock_progress):
    """Test updating phase progress."""
    phase_runner.start_phase("test_phase", 10)
    
    phase_runner.update_progress(
        files_processed=5,
        files_skipped=2,
        files_failed=1
    )
    
    stats = phase_runner.stats["test_phase"]
    assert stats.files_processed == 5
    assert stats.files_skipped == 2
    assert stats.files_failed == 1
    assert stats.files_remaining == 2
    
    mock_progress.update.assert_called_once_with(
        "test_task",
        completed=8,
        description="Processed: 5, Skipped: 2, Failed: 1, Remaining: 2"
    )


def test_phase_runner_end_phase(phase_runner, mock_progress):
    """Test ending a phase."""
    phase_runner.start_phase("test_phase", 10)
    phase_runner.update_progress(files_processed=8, files_skipped=1, files_failed=1)
    
    with patch.object(phase_runner.logger, 'info') as mock_info:
        with patch.object(phase_runner.logger.console, 'print') as mock_print:
            phase_runner.end_phase()
            
            assert phase_runner.current_phase is None
            assert phase_runner._progress is None
            assert phase_runner._task is None
            
            mock_info.assert_any_call("Phase complete: test_phase")
            mock_progress.stop.assert_called_once()
            
            # Verify that the last call was to print the table
            assert isinstance(mock_print.call_args_list[-1][0][0], Table)


def test_phase_runner_get_stats(phase_runner):
    """Test getting phase statistics."""
    phase_runner.start_phase("phase1", 10)
    phase_runner.update_progress(files_processed=5)
    phase_runner.end_phase()
    
    phase_runner.start_phase("phase2", 20)
    phase_runner.update_progress(files_processed=15)
    phase_runner.end_phase()
    
    # Test get_phase_stats
    stats1 = phase_runner.get_phase_stats("phase1")
    assert stats1 is not None
    assert stats1.phase_name == "phase1"
    assert stats1.total_files == 10
    assert stats1.files_processed == 5
    
    # Test get_all_stats
    all_stats = phase_runner.get_all_stats()
    assert len(all_stats) == 2
    assert {s.phase_name for s in all_stats} == {"phase1", "phase2"}


def test_phase_runner_no_current_phase(phase_runner):
    """Test operations with no current phase."""
    # Update progress without starting phase
    phase_runner.update_progress(files_processed=5)
    assert not phase_runner.stats
    
    # End phase without starting one
    phase_runner.end_phase()
    assert not phase_runner.stats
    
    # Get stats for non-existent phase
    assert phase_runner.get_phase_stats("nonexistent") is None


def test_phase_runner_multiple_phases(phase_runner):
    """Test running multiple phases sequentially."""
    # Phase 1
    phase_runner.start_phase("phase1", 10)
    phase_runner.update_progress(files_processed=10)
    phase_runner.end_phase()
    
    # Phase 2
    phase_runner.start_phase("phase2", 5)
    phase_runner.update_progress(files_processed=3, files_failed=2)
    phase_runner.end_phase()
    
    # Verify stats
    stats1 = phase_runner.get_phase_stats("phase1")
    assert stats1.success_rate == 100.0
    
    stats2 = phase_runner.get_phase_stats("phase2")
    assert stats2.success_rate == 60.0
    
    # Verify all phases are complete
    assert phase_runner.current_phase is None
    assert len(phase_runner.get_all_stats()) == 2 