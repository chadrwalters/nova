"""Default configuration for markdown consolidate phase."""

from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    # Consolidation settings
    'consolidate': {
        # Attachment handling
        'attachment_markers': {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        },
        'attachment_handling': {
            'copy_attachments': True,
            'update_references': True,
            'preserve_structure': True,
            'maintain_hierarchy': True
        },
        'content_handling': {
            'merge_content': True,
            'preserve_headers': True,
            'add_file_markers': True,
            'add_navigation': True
        },
        'metadata': {
            'preserve_original': True,
            'combine_metadata': True,
            'track_sources': True
        }
    },
    
    # File organization
    'organization': {
        'group_by_root': True,
        'create_index': True,
        'directory_structure': {
            'attachments': 'attachments',
            'images': 'images',
            'documents': 'documents',
            'other': 'misc'
        }
    },
    
    # Link handling
    'links': {
        'update_paths': True,
        'validate_links': True,
        'create_relative_paths': True,
        'handle_missing': {
            'action': 'warn',  # or 'error', 'ignore'
            'placeholder': '[MISSING: {filename}]'
        }
    },
    
    # Processing options
    'processing': {
        'parallel_processing': True,
        'max_workers': 4,
        'chunk_size': 1000,
        'retry_count': 3,
        'timeout': 30  # seconds
    },
    
    # Error handling
    'error_handling': {
        'continue_on_error': True,
        'log_errors': True,
        'create_error_report': True,
        'rollback_on_failure': True
    }
} 