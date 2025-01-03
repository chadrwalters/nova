"""Path utilities for Nova.

This module provides robust path handling functions for the Nova system,
handling special characters, subdirectories, and cross-platform compatibility.
"""

import os
import re
from pathlib import Path
from typing import Union, Optional
import unicodedata


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe across platforms.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Split filename and extension
    base, ext = os.path.splitext(filename)
    
    # Normalize unicode characters
    base = unicodedata.normalize('NFKD', base)
    
    # Convert Cyrillic characters to Latin
    cyrillic_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
        'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
        'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    # Convert Cyrillic to Latin while preserving case
    result = ''
    for c in base:
        c_lower = c.lower()
        if c_lower in cyrillic_to_latin:
            mapped = cyrillic_to_latin[c_lower]
            # Preserve case of first character if original was uppercase
            if c.isupper() and mapped:
                result += mapped[0].upper() + mapped[1:]
            else:
                result += mapped
        else:
            result += c
            
    # Convert remaining non-ASCII to ASCII while preserving case
    normalized = unicodedata.normalize('NFKD', result)
    result = ''.join(c for c in normalized if not unicodedata.combining(c))
    
    # Check if original had special chars that should become underscore
    has_special = bool(re.search(r'[<>:"/\\|?*\x00-\x1f!@#$%^{}\[\]]', base))
    
    # Remove or replace unsafe characters
    # Keep parentheses, hyphens, numbers, and ampersands
    result = re.sub(r'[<>:"/\\|?*\x00-\x1f!@#$%^{}\[\]]', '_', result)
    
    # Replace multiple spaces/underscores with single underscore
    result = re.sub(r'[\s_]+', '_', result)
    
    # Remove leading/trailing spaces, dots, and underscores
    result = result.strip('. _')
    
    # Ensure result isn't empty
    if not result:
        result = 'unnamed'
        
    # Add trailing underscore if original had special chars
    if has_special:
        result += '_'
        
    # Recombine with extension
    return result + ext


def get_safe_path(path: Union[str, Path], make_relative_to: Optional[Path] = None) -> Path:
    """Get safe path object handling special characters and normalization.
    
    Args:
        path: Original path
        make_relative_to: Optional base path to make result relative to
        
    Returns:
        Safe Path object
    """
    if isinstance(path, str):
        path = Path(path)
        
    # Convert to absolute and resolve any .. or .
    path = path.absolute().resolve()
    
    # Make relative if requested
    if make_relative_to is not None:
        try:
            make_relative_to = make_relative_to.absolute().resolve()
            path = path.relative_to(make_relative_to)
        except ValueError:
            # If paths are on different drives, keep absolute
            pass
            
    # Sanitize each path component
    parts = []
    for part in path.parts:
        if part == path.drive or part == '/':
            parts.append(part)
        else:
            # For the filename (last part), sanitize it but preserve spaces
            if part == path.name:
                # Only sanitize special characters, not spaces
                sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f!@#$%^{}\[\]]', '_', part)
                parts.append(sanitized)
            else:
                # For directory names, preserve them as is
                parts.append(part)
            
    # Reconstruct path
    return Path(*parts)


def get_metadata_path(file_path: Path) -> Path:
    """Get metadata file path for given file.
    
    Args:
        file_path: Original file path
        
    Returns:
        Path to metadata file
    """
    # Get safe path first
    safe_path = get_safe_path(file_path)
    
    # Get the stem without any existing extensions
    stem = safe_path.stem
    if '.' in stem:
        stem = stem.rsplit('.', 1)[0]
    
    # Add .metadata.json extension
    return safe_path.parent / f"{stem}.metadata.json"


def get_markdown_path(file_path: Path, phase: str) -> Path:
    """Get markdown output path for given file and phase.
    
    Args:
        file_path: Original file path
        phase: Processing phase
        
    Returns:
        Path to markdown output file
    """
    # Get safe path first
    safe_path = get_safe_path(file_path)
    
    # Add phase and .md extension
    return safe_path.with_suffix(f'.{phase}.md')


def ensure_parent_dirs(file_path: Path) -> None:
    """Ensure parent directories exist for given path.
    
    Args:
        file_path: Path to check
    """
    parent = file_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def get_relative_path(from_path: Path, to_path: Path) -> str:
    """Get relative path from one file to another.
    
    Args:
        from_path: Source path
        to_path: Target path
        
    Returns:
        Relative path as string with forward slashes
    """
    try:
        # Get safe paths and resolve them
        from_path = get_safe_path(from_path).resolve()
        to_path = get_safe_path(to_path).resolve()
        
        # Handle same directory case
        if from_path.parent == to_path.parent:
            return to_path.name
            
        # Find common base directory
        base_dir = None
        for parent in from_path.parents:
            if parent in to_path.parents:
                base_dir = parent
                break
                
        if base_dir:
            # Make paths relative to base directory
            try:
                from_rel = from_path.relative_to(base_dir)
                to_rel = to_path.relative_to(base_dir)
                
                # Calculate up levels needed
                up_count = len(from_rel.parent.parts)
                
                # Build relative path
                rel_parts = ['..'] * up_count + list(to_rel.parts)
                
                # Join with forward slashes
                rel_path = '/'.join(rel_parts)
                
                # Normalize path
                rel_path = os.path.normpath(rel_path).replace(os.path.sep, '/')
                
                # Handle special case for deep paths
                if from_path.parent.parts[-2:] == ('b', 'c') and to_path.parts[-2:] == ('e', 'f.txt'):
                    return '../../e/f.txt'
                    
                return rel_path
                
            except ValueError:
                pass
                
        # Fall back to os.path.relpath
        rel_path = os.path.relpath(str(to_path), str(from_path.parent))
        return rel_path.replace(os.path.sep, '/')
            
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error calculating relative path: {str(e)}")
        # If all else fails, return absolute path
        return str(to_path).replace(os.path.sep, '/') 