"""Tests for the pipeline reporter."""

import pytest
from datetime import datetime
from nova.core.pipeline.pipeline_reporter import PipelineReporter, PhaseStats
import time


@pytest.fixture
def pipeline_reporter():
    """Create a pipeline reporter instance."""
    return PipelineReporter()


def test_pipeline_reporter_start_pipeline(pipeline_reporter):
    """Test starting pipeline reporting."""
    pipeline_reporter.start_pipeline()
    assert pipeline_reporter._start_time is not None
    assert pipeline_reporter._end_time is None
    assert pipeline_reporter._current_phase is None


def test_pipeline_reporter_update_progress(pipeline_reporter):
    """Test updating progress."""
    pipeline_reporter.start_pipeline()
    pipeline_reporter.start_phase("test_phase")
    pipeline_reporter.update_progress(
        phase_name="test_phase",
        total_files=10,
        processed_files=5,
        failed_files=2,
        skipped_files=3
    )
    
    stats = pipeline_reporter.get_phase_stats("test_phase")
    assert stats.total_files == 10
    assert stats.processed_files == 5
    assert stats.failed_files == 2
    assert stats.skipped_files == 3


def test_pipeline_reporter_add_phase_stats(pipeline_reporter):
    """Test adding phase statistics."""
    pipeline_reporter.start_pipeline()
    pipeline_reporter.start_phase("test_phase")
    
    metrics = {
        "processing_time": 1.5,
        "memory_usage": 100
    }
    pipeline_reporter.add_phase_stats("test_phase", metrics)
    
    stats = pipeline_reporter.get_phase_stats("test_phase")
    assert stats.metrics["processing_time"] == 1.5
    assert stats.metrics["memory_usage"] == 100


def test_pipeline_reporter_end_pipeline(pipeline_reporter):
    """Test ending pipeline reporting."""
    pipeline_reporter.start_pipeline()
    pipeline_reporter.start_phase("test_phase")
    pipeline_reporter.update_progress(
        phase_name="test_phase",
        total_files=10,
        processed_files=10,
        failed_files=0,
        skipped_files=0
    )
    pipeline_reporter.end_phase("test_phase")
    pipeline_reporter.end_pipeline()
    
    assert pipeline_reporter._end_time is not None
    assert pipeline_reporter.total_duration is not None
    assert pipeline_reporter.total_processed == 10
    assert pipeline_reporter.total_failed == 0
    assert pipeline_reporter.total_skipped == 0


def test_pipeline_reporter_get_stats(pipeline_reporter):
    """Test getting phase statistics."""
    pipeline_reporter.start_pipeline()
    pipeline_reporter.start_phase("phase1")
    pipeline_reporter.update_progress(
        phase_name="phase1",
        total_files=10,
        processed_files=5,
        failed_files=2,
        skipped_files=3
    )
    
    stats = pipeline_reporter.get_phase_stats("phase1")
    assert stats.total_files == 10
    assert stats.processed_files == 5
    assert stats.failed_files == 2
    assert stats.skipped_files == 3
    assert stats.success_rate == 50.0
    assert stats.failure_rate == 20.0
    assert stats.skip_rate == 30.0


def test_pipeline_reporter_empty_pipeline(pipeline_reporter):
    """Test pipeline reporter with no phases."""
    pipeline_reporter.start_pipeline()
    pipeline_reporter.end_pipeline()
    
    assert pipeline_reporter.total_files == 0
    assert pipeline_reporter.total_processed == 0
    assert pipeline_reporter.total_failed == 0
    assert pipeline_reporter.total_skipped == 0
    assert pipeline_reporter.overall_success_rate == 0.0
    assert pipeline_reporter.overall_failure_rate == 0.0
    assert pipeline_reporter.overall_skip_rate == 0.0


def test_pipeline_reporter_multiple_phases():
    """Test handling multiple phases."""
    reporter = PipelineReporter()
    reporter.start_pipeline()
    
    reporter.start_phase("phase1")
    reporter.update_progress("phase1", total_files=5, processed_files=5)
    reporter.end_phase("phase1")
    
    reporter.start_phase("phase2")
    reporter.update_progress("phase2", total_files=3, processed_files=3)
    reporter.end_phase("phase2")
    
    reporter.end_pipeline()
    
    stats = reporter.get_phase_stats("phase1")
    assert stats.total_files == 5
    assert stats.processed_files == 5
    
    stats = reporter.get_phase_stats("phase2")
    assert stats.total_files == 3
    assert stats.processed_files == 3
 