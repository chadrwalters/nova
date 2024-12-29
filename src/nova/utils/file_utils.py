"""File utility functions."""

from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

def safe_write_file(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
    """Write content to file only if it has changed.
    
    Args:
        file_path: Path to file.
        content: Content to write.
        encoding: File encoding.
        
    Returns:
        True if file was written, False if unchanged.
    """
    try:
        # Check if file exists and content matches
        if file_path.exists():
            try:
                current_content = file_path.read_text(encoding=encoding)
                if current_content == content:
                    return False
            except Exception:
                pass  # If reading fails, write the file
        
        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary file in the same directory
        temp_path = file_path.parent / f"{file_path.name}.tmp"
        
        # Write content to temporary file
        temp_path.write_text(content, encoding=encoding)
        
        # Use shutil.copy2 to preserve timestamps when moving to final location
        shutil.copy2(temp_path, file_path)
        
        # Clean up temporary file
        temp_path.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        raise 