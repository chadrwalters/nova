"""Default configuration for markdown parse phase."""

# Standard library imports
from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    # Markdown processing settings
    'markdown': {
        'document_conversion': True,
        'image_processing': True,
        'metadata_preservation': True,
        'preserve_formatting': True,
        'link_validation': True
    },
    
    # Image processing settings
    'image': {
        'formats': {
            'png': True,
            'jpg': True,
            'jpeg': True,
            'gif': True,
            'webp': True,
            'heic': True
        },
        'operations': {
            'format_conversion': {
                'heic_to_jpg': True,
                'optimize_quality': 85
            },
            'size_optimization': {
                'preserve_aspect_ratio': True,
                'max_dimensions': [1920, 1080]
            },
            'metadata': {
                'extract': True,
                'preserve_original': True
            }
        },
        'temp_files': {
            'use_stable_names': True,
            'cleanup_after_processing': True,
            'preserve_originals': True
        }
    },
    
    # Office document settings
    'office': {
        'formats': {
            'docx': {
                'extract_text': True,
                'preserve_paragraphs': True,
                'extract_images': True
            },
            'pptx': {
                'extract_slides': True,
                'include_notes': True,
                'extract_media': True
            },
            'xlsx': {
                'table_format': True,
                'preserve_headers': True,
                'all_sheets': True
            },
            'pdf': {
                'extract_text': True,
                'preserve_layout': True,
                'extract_images': True
            }
        },
        'operations': {
            'text_extraction': {
                'preserve_formatting': True,
                'handle_unicode': True
            },
            'image_extraction': {
                'process_embedded': True,
                'maintain_links': True
            },
            'metadata': {
                'preserve_all': True,
                'track_changes': True
            }
        }
    }
} 