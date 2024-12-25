"""Test pipeline configuration loading and validation."""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any

from nova.core.pipeline.manager import PipelineManager
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.errors import ConfigurationError, ValidationError, ErrorContext

@pytest.fixture
def pipeline_manager():
    """Create pipeline manager instance."""
    return PipelineManager(
        logger=logging.getLogger(__name__),
        error_tracker=ErrorTracker(logging.getLogger(__name__))
    )

async def test_load_valid_config(pipeline_manager):
    """Test loading a valid pipeline configuration."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'MARKDOWN_PARSE': {
                        'description': 'Parse markdown files',
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
    
    await pipeline_manager.load_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert report['is_valid']
    assert len(report['errors']) == 0
    assert report['total_errors'] == 0

async def test_load_invalid_config(pipeline_manager):
    """Test loading an invalid pipeline configuration."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'invalid-phase-name': {
                        'description': 'Invalid phase name',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        }
    }
    
    await pipeline_manager.load_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('phase name pattern' in str(err['message']) for err in report['errors'])

def test_validate_invalid_config(pipeline_manager):
    """Test validating an invalid pipeline configuration."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'invalid-phase-name': {
                        'description': 'Invalid phase name',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        }
    }
    
    pipeline_manager.schema_validator.validate_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('output_dir' in str(err['message']) for err in report['errors'])

def test_validate_invalid_phase_name(pipeline_manager):
    """Test validating a configuration with an invalid phase name."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'invalid-phase-name': {
                        'description': 'Invalid phase name',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        }
    }
    
    pipeline_manager.schema_validator.validate_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('phase name pattern' in str(err['message']) for err in report['errors'])

def test_validate_invalid_log_level(pipeline_manager):
    """Test validating a configuration with an invalid log level."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        },
        'logging': {
            'level': 'INVALID_LEVEL'
        }
    }
    
    pipeline_manager.schema_validator.validate_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('log level' in str(err['message']).lower() for err in report['errors'])

def test_validate_component_structure(pipeline_manager):
    """Test validating a configuration with an invalid component structure."""
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
                                    'unknown_option': 'value'
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
    
    pipeline_manager.schema_validator.validate_config(config)
    report = pipeline_manager.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('unknown_option' in str(err['message']) for err in report['errors']) 