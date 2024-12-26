"""Tests for schema validator."""

import pytest
from pathlib import Path
from typing import Dict, Any

from nova.core.schema_validator import SchemaValidator, DEFAULT_SCHEMA_PATH
from nova.core.error_tracker import ErrorTracker

@pytest.fixture
def validator():
    """Create schema validator instance."""
    return SchemaValidator(
        logger=logging.getLogger(__name__),
        error_tracker=ErrorTracker(logging.getLogger(__name__))
    )

@pytest.fixture
def valid_config():
    """Create valid pipeline configuration."""
    return {
        "pipeline": {
            "components": {
                "markdown_processor": {
                    "parser": "markitdown==0.0.1a3",
                    "config": {
                        "document_conversion": True,
                        "image_processing": True,
                        "metadata_preservation": True
                    }
                },
                "image_processor": {
                    "formats": ["png", "jpg/jpeg", "gif"],
                    "operations": [
                        {
                            "format_conversion": {
                                "heic_to_jpg": True,
                                "optimize_quality": 85
                            }
                        },
                        {
                            "size_optimization": {
                                "preserve_aspect_ratio": True,
                                "max_dimensions": [1920, 1080]
                            }
                        }
                    ]
                }
            },
            "phases": [
                {
                    "MARKDOWN_PARSE": {
                        "description": "Parse markdown files",
                        "output_dir": "${NOVA_PHASE_MARKDOWN_PARSE}",
                        "processor": "MarkdownProcessor",
                        "enabled": True,
                        "handlers": [
                            {
                                "type": "MarkdownHandler",
                                "base_handler": "nova.phases.core.base_handler.BaseHandler",
                                "options": {
                                    "document_conversion": True
                                }
                            }
                        ]
                    }
                }
            ]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "default"
                }
            },
            "use_rich": True
        }
    }

@pytest.fixture
def invalid_config():
    """Create invalid pipeline configuration."""
    return {
        "pipeline": {
            "components": {
                "markdown_processor": {
                    "parser": "invalid",  # Invalid parser version format
                    "config": "not_an_object"  # Should be object
                },
                "image_processor": {
                    "formats": ["invalid_format"],  # Invalid format
                    "operations": [
                        {
                            "invalid_operation": {}  # Invalid operation
                        }
                    ]
                }
            },
            "phases": [
                {
                    "invalid_phase_name": {  # Invalid phase name pattern
                        "description": 123,  # Should be string
                        "processor": "InvalidProcessor"  # Missing output_dir
                    }
                }
            ]
        }
    }

def test_validate_valid_config():
    """Test validating a valid configuration."""
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
    
    validator = SchemaValidator()
    report = validator.get_validation_report()
    
    assert report['is_valid']
    assert len(report['errors']) == 0
    assert report['total_errors'] == 0

def test_validate_invalid_config():
    """Test validating an invalid configuration."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'invalid_phase_name': {
                        'description': 'Invalid phase name',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('phase name pattern' in str(err['message']) for err in report['errors'])

def test_validate_missing_required_fields():
    """Test validating a configuration with missing required fields."""
    config = {
        'pipeline': {
            # Missing required 'phases' field
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('required property' in str(err['message']) for err in report['errors'])

def test_validate_invalid_phase_name():
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
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('phase name pattern' in str(err['message']) for err in report['errors'])

def test_validate_invalid_handler_config():
    """Test validating a configuration with invalid handler configuration."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'handlers': [
                            {
                                'type': 'TestHandler',
                                'document_conversion': True
                                # Missing required base_handler
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('base_handler' in str(err['message']) for err in report['errors'])

def test_validate_invalid_image_dimensions():
    """Test validating a configuration with invalid image dimensions."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'components': {
                            'image_processor': {
                                'formats': ['png'],
                                'operations': [
                                    {
                                        'size_optimization': {
                                            'preserve_aspect_ratio': True,
                                            'max_dimensions': [0, 1080]  # Invalid dimension
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('dimensions' in str(err['message']) for err in report['errors'])

def test_validate_invalid_log_level():
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
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('log level' in str(err['message']).lower() for err in report['errors'])

def test_validate_component_structure():
    """Test validating a configuration with an invalid component structure."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'TEST_PHASE': {
                        'description': 'Test phase',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor',
                        'components': [
                            {
                                'markdown_processor': {
                                    'parser': 'markitdown==0.0.1a3',
                                    'config': {}
                                }
                            }
                        ]  # Invalid structure (array instead of object)
                    }
                }
            ]
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    report = validator.get_validation_report()
    
    assert not report['is_valid']
    assert len(report['errors']) > 0
    assert report['total_errors'] > 0
    assert any('components structure' in str(err['message']) for err in report['errors'])

def test_clear_validation_state():
    """Test clearing validation state."""
    config = {
        'pipeline': {
            'phases': [
                {
                    'invalid_phase_name': {
                        'description': 'Invalid phase name',
                        'output_dir': '${NOVA_PHASE_MARKDOWN_PARSE}',
                        'processor': 'MarkdownProcessor'
                    }
                }
            ]
        }
    }
    
    validator = SchemaValidator()
    validator.validate_config(config)
    assert len(validator.validation_errors) > 0
    
    validator.clear_validation_state()
    assert len(validator.validation_errors) == 0 