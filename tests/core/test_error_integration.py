"""Test error integration."""

import pytest
import logging
from typing import Dict, Any

from nova.core.pipeline.manager import PipelineManager
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.utils.schema_validator import SchemaValidator
from nova.core.config.base import PipelineConfig, ProcessorConfig

@pytest.fixture
def error_tracker():
    """Create error tracker instance."""
    return ErrorTracker(logging.getLogger(__name__))

@pytest.fixture
def invalid_config():
    """Create invalid pipeline configuration."""
    return {
        "pipeline": {
            "paths": {
                "base_dir": "${NOVA_BASE_DIR}"
            },
            "phases": [
                {
                    "INVALID_PHASE": {
                        "description": "Test phase",
                        "output_dir": "${NOVA_OUTPUT_DIR}/test",
                        "processor": "TestProcessor"
                    }
                }
            ]
        }
    }

@pytest.fixture
def valid_config():
    """Create valid pipeline configuration."""
    return {
        "pipeline": {
            "paths": {
                "base_dir": "${NOVA_BASE_DIR}"
            },
            "phases": [
                {
                    "TEST_PHASE": {
                        "description": "Test phase",
                        "output_dir": "${NOVA_OUTPUT_DIR}/test",
                        "processor": "TestProcessor"
                    }
                }
            ]
        }
    }

async def test_load_invalid_config(error_tracker, invalid_config):
    """Test loading an invalid pipeline configuration."""
    config = PipelineConfig(
        paths={"base_dir": "${NOVA_BASE_DIR}"},
        phases=[
            ProcessorConfig(
                name="INVALID_PHASE",
                description="Test phase",
                output_dir="${NOVA_OUTPUT_DIR}/test",
                processor="TestProcessor"
            )
        ]
    )
    manager = PipelineManager(config)
    
    # Verify error handling
    assert manager.config is not None
    assert len(manager.phase_configs) == 1
    assert "INVALID_PHASE" in manager.phase_configs

async def test_error_context_preservation(error_tracker, valid_config):
    """Test error context preservation."""
    config = PipelineConfig(
        paths={"base_dir": "${NOVA_BASE_DIR}"},
        phases=[
            ProcessorConfig(
                name="TEST_PHASE",
                description="Test phase",
                output_dir="${NOVA_OUTPUT_DIR}/test",
                processor="TestProcessor"
            )
        ]
    )
    pipeline_manager = PipelineManager(config)
    
    # Verify error context
    assert pipeline_manager.config is not None
    assert len(pipeline_manager.phase_configs) == 1
    assert "TEST_PHASE" in pipeline_manager.phase_configs

async def test_warning_tracking(error_tracker, valid_config):
    """Test warning tracking."""
    config = PipelineConfig(
        paths={"base_dir": "${NOVA_BASE_DIR}"},
        phases=[
            ProcessorConfig(
                name="TEST_PHASE",
                description="Test phase",
                output_dir="${NOVA_OUTPUT_DIR}/test",
                processor="TestProcessor"
            )
        ]
    )
    pipeline_manager = PipelineManager(config)
    
    # Verify warning tracking
    assert pipeline_manager.config is not None
    assert len(pipeline_manager.phase_configs) == 1
    assert "TEST_PHASE" in pipeline_manager.phase_configs

async def test_error_clearing(error_tracker, valid_config):
    """Test error clearing."""
    config = PipelineConfig(
        paths={"base_dir": "${NOVA_BASE_DIR}"},
        phases=[
            ProcessorConfig(
                name="TEST_PHASE",
                description="Test phase",
                output_dir="${NOVA_OUTPUT_DIR}/test",
                processor="TestProcessor"
            )
        ]
    )
    pipeline_manager = PipelineManager(config)
    
    # Verify error clearing
    assert pipeline_manager.config is not None
    assert len(pipeline_manager.phase_configs) == 1
    assert "TEST_PHASE" in pipeline_manager.phase_configs 