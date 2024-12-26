"""Tests for component handler."""

import pytest
from pathlib import Path

from nova.core.component_handler import ComponentHandler
from nova.core.errors import ComponentError, ConfigurationError

@pytest.fixture
def handler():
    """Create component handler instance."""
    return ComponentHandler()

@pytest.fixture
def valid_markdown_config():
    """Create valid markdown processor configuration."""
    return {
        'parser': 'markitdown==0.0.1a3',
        'config': {
            'document_conversion': True,
            'image_processing': True,
            'metadata_preservation': True
        },
        'handlers': [{
            'base_handler': 'nova.phases.core.base_handler.BaseHandler'
        }]
    }

@pytest.fixture
def valid_image_config():
    """Create valid image processor configuration."""
    return {
        'formats': ['png', 'jpg/jpeg', 'gif'],
        'operations': [
            {
                'format_conversion': {
                    'heic_to_jpg': True,
                    'optimize_quality': 85
                }
            }
        ],
        'temp_files': {
            'use_stable_names': True,
            'cleanup_after_processing': True,
            'preserve_originals': True
        }
    }

@pytest.fixture
def valid_office_config():
    """Create valid office processor configuration."""
    return {
        'formats': {
            'docx/doc': {
                'extract_text': True,
                'preserve_paragraphs': True
            },
            'pdf': {
                'extract_text': True,
                'preserve_layout': True
            }
        },
        'operations': [
            {
                'text_extraction': {
                    'preserve_formatting': True,
                    'handle_unicode': True
                }
            }
        ],
        'content_extraction': {
            'try_attributes': ['text_content', 'markdown', 'text'],
            'fallback_to_dict': True,
            'log_failures': True
        }
    }

@pytest.mark.asyncio
async def test_apply_markdown_config(handler, valid_markdown_config):
    """Test applying valid markdown processor configuration."""
    config = await handler.apply_component_config(
        'markdown_processor',
        valid_markdown_config
    )
    assert config == valid_markdown_config
    assert not handler.get_warnings()

@pytest.mark.asyncio
async def test_apply_image_config(handler, valid_image_config):
    """Test applying valid image processor configuration."""
    config = await handler.apply_component_config(
        'image_processor',
        valid_image_config
    )
    assert config == valid_image_config
    assert not handler.get_warnings()

@pytest.mark.asyncio
async def test_apply_office_config(handler, valid_office_config):
    """Test applying valid office processor configuration."""
    config = await handler.apply_component_config(
        'office_processor',
        valid_office_config
    )
    assert config == valid_office_config
    assert not handler.get_warnings()

@pytest.mark.asyncio
async def test_invalid_component_type(handler, valid_markdown_config):
    """Test handling invalid component type."""
    with pytest.raises(ComponentError) as exc:
        await handler.apply_component_config(
            'invalid_processor',
            valid_markdown_config
        )
    assert 'Unknown component type' in str(exc.value)

@pytest.mark.asyncio
async def test_missing_required_field(handler, valid_markdown_config):
    """Test handling missing required field."""
    del valid_markdown_config['parser']
    with pytest.raises(ConfigurationError) as exc:
        await handler.apply_component_config(
            'markdown_processor',
            valid_markdown_config
        )
    assert 'Missing required field' in str(exc.value)

@pytest.mark.asyncio
async def test_invalid_field_type(handler, valid_markdown_config):
    """Test handling invalid field type."""
    valid_markdown_config['handlers'] = 'invalid'
    with pytest.raises(ConfigurationError) as exc:
        await handler.apply_component_config(
            'markdown_processor',
            valid_markdown_config
        )
    assert 'must be list' in str(exc.value)

@pytest.mark.asyncio
async def test_non_standard_parser(handler, valid_markdown_config):
    """Test handling non-standard parser version."""
    valid_markdown_config['parser'] = 'custom_parser'
    config = await handler.apply_component_config(
        'markdown_processor',
        valid_markdown_config
    )
    warnings = handler.get_warnings()
    assert len(warnings) == 1
    assert 'Non-standard parser version' in warnings[0]['message']

@pytest.mark.asyncio
async def test_missing_config_keys(handler, valid_markdown_config):
    """Test handling missing configuration keys."""
    del valid_markdown_config['config']['document_conversion']
    config = await handler.apply_component_config(
        'markdown_processor',
        valid_markdown_config
    )
    warnings = handler.get_warnings()
    assert len(warnings) == 1
    assert 'Using default value' in warnings[0]['message']
    assert config['config']['document_conversion'] is True

@pytest.mark.asyncio
async def test_unsupported_image_format(handler, valid_image_config):
    """Test handling unsupported image format."""
    valid_image_config['formats'].append('unsupported')
    config = await handler.apply_component_config(
        'image_processor',
        valid_image_config
    )
    warnings = handler.get_warnings()
    assert len(warnings) == 1
    assert 'Unsupported format' in warnings[0]['message']

@pytest.mark.asyncio
async def test_missing_temp_files_config(handler, valid_image_config):
    """Test handling missing temp files configuration."""
    del valid_image_config['temp_files']['use_stable_names']
    config = await handler.apply_component_config(
        'image_processor',
        valid_image_config
    )
    warnings = handler.get_warnings()
    assert len(warnings) == 1
    assert 'Using default value' in warnings[0]['message']
    assert config['temp_files']['use_stable_names'] is True

@pytest.mark.asyncio
async def test_missing_content_extraction(handler, valid_office_config):
    """Test handling missing content extraction configuration."""
    del valid_office_config['content_extraction']['try_attributes']
    config = await handler.apply_component_config(
        'office_processor',
        valid_office_config
    )
    warnings = handler.get_warnings()
    assert len(warnings) == 1
    assert 'Using default try_attributes' in warnings[0]['message']
    assert 'text_content' in config['content_extraction']['try_attributes'] 