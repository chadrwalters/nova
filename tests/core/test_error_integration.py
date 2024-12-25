"""Test error integration."""

import pytest
import logging
from typing import Dict, Any

from nova.core.pipeline.manager import PipelineManager
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.utils.schema_validator import SchemaValidator

@pytest.fixture
def error_tracker():
    """Create error tracker instance."""
    return ErrorTracker(logging.getLogger(__name__))

@pytest.fixture
def invalid_config():
    """Create invalid pipeline configuration."""
    return {
        "pipeline": {
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

async def test_load_invalid_config(error_tracker):
    """Test loading invalid configuration."""
    manager = PipelineManager(
        logger=logging.getLogger(__name__),
        error_tracker=error_tracker
    )
    
    config = {
        "pipeline": {
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
    
    try:
        await manager.load_config(config)
    except Exception as e:
        error_report = manager.get_validation_report()
        assert error_report['total_errors'] > 0
        assert any(
            'INVALID_PHASE' in str(err['message'])
            for err in error_report['errors']
        )

async def test_error_context_preservation():
    """Test error context preservation across components."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'components': {
                            'markdown_processor': {
                                'parser': 'markitdown==0.0.1a3',
                                'config': {
                                    'unknown_option': True
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
    
    # Create test components
    error_tracker = ErrorTracker()
    schema_validator = SchemaValidator()
    pipeline_manager = PipelineManager()
    
    # Add errors with context
    error_tracker.add_error('test_component', 'Test error message', {'key': 'value'})
    schema_validator.validate_config(config)
    await pipeline_manager.load_config(config)
    
    # Get error report
    error_report = pipeline_manager.get_validation_report()
    
    # Check error context preservation
    assert error_report['total_errors'] > 0
    assert any(err.get('context') is not None for err in error_report['errors'])

async def test_warning_tracking():
    """Test warning tracking across components."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'components': {
                            'markdown_processor': {
                                'parser': 'markitdown==0.0.1a3',
                                'config': {}
                            }
                        }
                    }
                }
            ]
        }
    }
    
    # Create test components
    error_tracker = ErrorTracker()
    schema_validator = SchemaValidator(error_tracker=error_tracker)
    pipeline_manager = PipelineManager(error_tracker=error_tracker)
    
    # Add warnings to components
    error_tracker.add_warning('test_component', 'Test warning message')
    schema_validator.validate_config(config)
    await pipeline_manager.load_config(config)
    
    # Get error report
    error_report = pipeline_manager.get_validation_report()
    
    # Check warning tracking
    assert error_report['total_warnings'] > 0
    assert any('Test warning message' in str(warn['message']) for warn in error_report['warnings'])

async def test_error_clearing():
    """Test error clearing across components."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'components': {
                            'markdown_processor': {
                                'parser': 'markitdown==0.0.1a3',
                                'config': {}
                            }
                        }
                    }
                }
            ]
        }
    }
    
    # Create test components
    error_tracker = ErrorTracker()
    schema_validator = SchemaValidator(error_tracker=error_tracker)
    pipeline_manager = PipelineManager(error_tracker=error_tracker)
    
    # Add errors and warnings
    error_tracker.add_error('test_component', 'Test error message')
    error_tracker.add_warning('test_component', 'Test warning message')
    schema_validator.validate_config(config)
    await pipeline_manager.load_config(config)
    
    # Get initial error report
    error_report = pipeline_manager.get_validation_report()
    assert error_report['total_errors'] > 0
    assert error_report['total_warnings'] > 0
    
    # Clear errors
    error_tracker.clear()
    schema_validator.clear_validation_state()
    pipeline_manager.clear_state()
    
    # Get updated error report
    error_report = pipeline_manager.get_validation_report()
    assert error_report['total_errors'] == 0
    assert error_report['total_warnings'] == 0 