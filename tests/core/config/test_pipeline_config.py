"""Tests for pipeline configuration."""

import os
import pytest
from pathlib import Path

from nova.core.config.pipeline_config import PipelineConfig, PhaseConfig
from nova.core.errors import ValidationError


def test_phase_config_basic():
    """Test basic phase configuration."""
    config = {
        "description": "Test phase",
        "processor": str,  # Using str as a dummy processor
        "components": {
            "test_component": {
                "config": {"key": "value"}
            }
        },
        "output_dir": "/tmp/test"
    }
    
    phase = PhaseConfig("test_phase", config)
    assert phase.name == "test_phase"
    assert phase.description == "Test phase"
    assert phase.processor == str
    assert phase.components == {"test_component": {"config": {"key": "value"}}}
    assert phase.get_output_dir() == Path("/tmp/test")
    assert phase.get_dependencies() == []


def test_phase_config_validation():
    """Test phase configuration validation."""
    # Missing required keys
    config = {
        "description": "Test phase"
    }
    
    phase = PhaseConfig("test_phase", config)
    with pytest.raises(ValidationError, match="Missing required key"):
        phase.validate()
        
    # Invalid processor
    config = {
        "processor": "not_callable",
        "components": {}
    }
    
    phase = PhaseConfig("test_phase", config)
    with pytest.raises(ValidationError, match="Processor must be callable"):
        phase.validate()


def test_pipeline_config_basic(tmp_path):
    """Test basic pipeline configuration."""
    # Create test directories
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    
    # Create all directories including phase output dirs
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase1").parent.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase2").parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        "phases": {
            "phase1": {
                "description": "Phase 1",
                "processor": str,
                "components": {},
                "output_dir": str(output_dir / "phase1")
            },
            "phase2": {
                "description": "Phase 2",
                "processor": str,
                "components": {},
                "output_dir": str(output_dir / "phase2"),
                "dependencies": ["phase1"]
            }
        },
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "temp_dir": str(temp_dir)
    }
    
    pipeline = PipelineConfig(config)
    assert len(pipeline.phases) == 2
    assert "phase1" in pipeline.phases
    assert "phase2" in pipeline.phases
    assert pipeline.input_dir == input_dir
    assert pipeline.output_dir == output_dir
    assert pipeline.temp_dir == temp_dir
    assert pipeline.get_phase_dependencies("phase2") == ["phase1"]


def test_pipeline_config_env_vars(tmp_path, monkeypatch):
    """Test pipeline configuration with environment variables."""
    # Set up test environment variables
    monkeypatch.setenv("TEST_INPUT_DIR", str(tmp_path / "input"))
    monkeypatch.setenv("TEST_OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("TEST_TEMP_DIR", str(tmp_path / "temp"))
    
    # Create test directories
    input_dir = Path(os.environ["TEST_INPUT_DIR"])
    output_dir = Path(os.environ["TEST_OUTPUT_DIR"])
    temp_dir = Path(os.environ["TEST_TEMP_DIR"])
    phase_dir = output_dir / "test_phase"
    
    # Create all directories
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        "phases": {
            "test_phase": {
                "description": "Test phase",
                "processor": str,
                "components": {},
                "output_dir": "${TEST_OUTPUT_DIR}/test_phase"
            }
        },
        "input_dir": "${TEST_INPUT_DIR}",
        "output_dir": "${TEST_OUTPUT_DIR}",
        "temp_dir": "${TEST_TEMP_DIR}"
    }
    
    pipeline = PipelineConfig(config)
    assert pipeline.input_dir == input_dir
    assert pipeline.output_dir == output_dir
    assert pipeline.temp_dir == temp_dir


def test_pipeline_config_validation():
    """Test pipeline configuration validation."""
    # Missing required keys
    config = {
        "phases": {}
    }
    
    with pytest.raises(ValidationError, match="Missing required key"):
        PipelineConfig(config)
        
    # Unknown phase dependency
    config = {
        "phases": {
            "phase1": {
                "description": "Phase 1",
                "processor": str,
                "components": {},
                "output_dir": "/tmp/test",
                "dependencies": ["unknown_phase"]
            }
        },
        "input_dir": "/tmp/input",
        "output_dir": "/tmp/output",
        "temp_dir": "/tmp/temp"
    }
    
    with pytest.raises(ValidationError, match="Unknown dependency"):
        PipelineConfig(config) 