"""Default configuration for markdown aggregate phase."""

from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    # Aggregation settings
    'aggregate': {
        # Section markers
        'section_markers': {
            'start': '<!-- START_FILE: {filename} -->',
            'end': '<!-- END_FILE: {filename} -->',
            'separator': '\n---\n'
        },
        
        # Content organization
        'organization': {
            'add_table_of_contents': True,
            'preserve_headers': True,
            'add_file_markers': True,
            'add_navigation': True,
            'include_metadata': True
        },
        
        # File sorting
        'sorting': {
            'sort_by': 'name',  # 'name', 'modified', 'size'
            'sort_reverse': False,
            'group_by_directory': True,
            'preserve_hierarchy': True
        },
        
        # Table of contents
        'toc': {
            'enabled': True,
            'max_depth': 3,
            'include_numbers': True,
            'style': 'bullet',  # 'bullet' or 'number'
            'collapse_single_items': True
        },
        
        # Navigation
        'navigation': {
            'add_prev_next': True,
            'add_top_link': True,
            'link_style': 'text',  # 'text' or 'arrow'
            'position': 'bottom'  # 'top', 'bottom', or 'both'
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
    
    # Output formatting
    'formatting': {
        'line_endings': 'lf',  # 'lf' or 'crlf'
        'ensure_final_newline': True,
        'trim_trailing_whitespace': True,
        'max_line_length': 80,
        'wrap_text': False
    },
    
    # Error handling
    'error_handling': {
        'continue_on_error': True,
        'log_errors': True,
        'create_error_report': True
    }
} 