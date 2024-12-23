#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from pipeline_manager import PipelineManager, PipelinePhase

@pytest.fixture
def setup_env(tmp_path):
    """Set up test environment variables."""
    os.environ["NOVA_BASE_DIR"] = str(tmp_path / "nova")
    os.environ["NOVA_INPUT_DIR"] = str(tmp_path / "nova/input")
    os.environ["NOVA_OUTPUT_DIR"] = str(tmp_path / "nova/output")
    os.environ["NOVA_PROCESSING_DIR"] = str(tmp_path / "nova/processing")
    os.environ["NOVA_TEMP_DIR"] = str(tmp_path / "nova/temp")
    os.environ["NOVA_PHASE_MARKDOWN_PARSE"] = str(tmp_path / "nova/processing/phase1")
    os.environ["NOVA_PHASE_MARKDOWN_CONSOLIDATE"] = str(tmp_path / "nova/processing/phase2")
    os.environ["NOVA_PHASE_MARKDOWN_AGGREGATE"] = str(tmp_path / "nova/processing/phase3")
    os.environ["NOVA_PHASE_MARKDOWN_SPLIT"] = str(tmp_path / "nova/processing/phase4")
    
    return tmp_path

@pytest.fixture
def create_test_files(setup_env):
    """Create test files for pipeline testing."""
    input_dir = setup_env / "nova" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test markdown files
    test1_content = """--==SUMMARY==--
# Test Document 1
This is a summary of document 1.

--==RAW NOTES==--
## Section 1
This is some test content.
![Test Image](test_image.jpg)

--==ATTACHMENTS==--
[PDF Document](test_doc.pdf)
"""
    
    test2_content = """--==SUMMARY==--
# Test Document 2
This is a summary of document 2.

--==RAW NOTES==--
## Section 2
More test content here.
[Another PDF](test_doc.pdf)

--==ATTACHMENTS==--
Some attachment content.
"""
    
    # Write test files
    (input_dir / "test1.md").write_text(test1_content)
    (input_dir / "test2.md").write_text(test2_content)
    
    # Create dummy attachments
    (input_dir / "test_image.jpg").write_text("dummy image content")
    (input_dir / "test_doc.pdf").write_text("dummy pdf content")
    
    return [input_dir / "test1.md", input_dir / "test2.md", input_dir / "test_image.jpg", input_dir / "test_doc.pdf"]

def test_pipeline_initialization(setup_env):
    """Test pipeline manager initialization."""
    pipeline = PipelineManager()
    assert pipeline.base_dir.exists()
    assert pipeline.input_dir.exists()
    assert pipeline.output_dir.exists()
    assert pipeline.processing_dir.exists()
    assert pipeline.temp_dir.exists()
    
    for phase_dir in pipeline.phase_dirs.values():
        assert phase_dir.exists()

def test_pipeline_full_run(setup_env, create_test_files):
    """Test running the complete pipeline."""
    pipeline = PipelineManager()
    success = pipeline.run_pipeline()
    assert success
    
    # Check phase outputs
    phase1_dir = pipeline.phase_dirs[PipelinePhase.MARKDOWN_PARSE]
    phase2_dir = pipeline.phase_dirs[PipelinePhase.MARKDOWN_CONSOLIDATE]
    phase3_dir = pipeline.phase_dirs[PipelinePhase.MARKDOWN_AGGREGATE]
    phase4_dir = pipeline.phase_dirs[PipelinePhase.MARKDOWN_SPLIT_THREEFILES]
    
    # Check phase 1 output
    assert (phase1_dir / "test1.md").exists()
    assert (phase1_dir / "test2.md").exists()
    
    # Check phase 2 output
    assert (phase2_dir / "test1.md").exists()
    assert (phase2_dir / "test2.md").exists()
    assert (phase2_dir / "test1_attachments").exists()
    assert (phase2_dir / "test2_attachments").exists()
    
    # Check phase 3 output
    assert (phase3_dir / "all_merged_markdown.md").exists()
    content = (phase3_dir / "all_merged_markdown.md").read_text()
    assert "# Test Document 1" in content
    assert "# Test Document 2" in content
    assert "File Index" in content
    
    # Check phase 4 output
    assert (phase4_dir / "summary.md").exists()
    assert (phase4_dir / "raw_notes.md").exists()
    assert (phase4_dir / "attachments.md").exists()
    
    # Check split file contents
    summary = (phase4_dir / "summary.md").read_text()
    raw_notes = (phase4_dir / "raw_notes.md").read_text()
    attachments = (phase4_dir / "attachments.md").read_text()
    
    # Check summary content
    assert "Test Document 1" in summary
    assert "summary of document 1" in summary
    assert "Test Document 2" in summary
    assert "summary of document 2" in summary
    
    # Check raw notes content
    assert "Section 1" in raw_notes
    assert "This is some test content" in raw_notes
    assert "Section 2" in raw_notes
    assert "More test content here" in raw_notes
    
    # Check attachments content
    assert "test_image.jpg" in attachments
    assert "test_doc.pdf" in attachments

def test_pipeline_partial_run(setup_env):
    """Test running a subset of pipeline phases."""
    pipeline = PipelineManager()
    success = pipeline.run_pipeline(
        start_phase=PipelinePhase.MARKDOWN_PARSE,
        end_phase=PipelinePhase.MARKDOWN_CONSOLIDATE
    )
    assert success

def test_pipeline_single_phase(setup_env):
    """Test running a single pipeline phase."""
    pipeline = PipelineManager()
    success = pipeline.process_phase(PipelinePhase.MARKDOWN_PARSE)
    assert success

def test_pipeline_invalid_phase(setup_env):
    """Test handling of invalid pipeline phase."""
    pipeline = PipelineManager()
    with pytest.raises(ValueError):
        pipeline.process_phase("INVALID_PHASE")

def test_pipeline_missing_env(monkeypatch):
    """Test handling of missing environment variables."""
    # Clear all required environment variables
    env_vars = [
        "NOVA_BASE_DIR",
        "NOVA_INPUT_DIR",
        "NOVA_OUTPUT_DIR",
        "NOVA_PROCESSING_DIR",
        "NOVA_TEMP_DIR",
        "NOVA_PHASE_MARKDOWN_PARSE",
        "NOVA_PHASE_MARKDOWN_CONSOLIDATE",
        "NOVA_PHASE_MARKDOWN_AGGREGATE",
        "NOVA_PHASE_MARKDOWN_SPLIT"
    ]
    
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    
    with pytest.raises(ValueError):
        PipelineManager()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 