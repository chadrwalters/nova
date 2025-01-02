"""File utility functions."""

import os
import shutil
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

def safe_write_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
    """Write content to file only if it has changed.
    
    Args:
        file_path: Path to file.
        content: Content to write.
        encoding: File encoding.
        
    Returns:
        True if file was written, False if unchanged.
    """
    try:
        # Convert to Path object
        file_path = Path(file_path)
        
        logger.debug(f"Writing file: {file_path}")
        logger.debug(f"Content length: {len(content)}")
        logger.debug(f"Parent directory: {file_path.parent}")
        
        # Check if file exists and content matches
        if file_path.exists():
            try:
                current_content = file_path.read_text(encoding=encoding)
                if current_content == content:
                    logger.debug("Content unchanged, skipping write")
                    return False
            except Exception as e:
                logger.debug(f"Error reading existing file: {str(e)}")
                pass  # If reading fails, write the file
        
        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created parent directory: {file_path.parent}")
        
        # Create a temporary file in the same directory
        temp_path = file_path.parent / f"{file_path.name}.tmp"
        logger.debug(f"Writing to temporary file: {temp_path}")
        
        # Write content to temporary file
        temp_path.write_text(content, encoding=encoding)
        logger.debug("Successfully wrote content to temporary file")
        
        # Use shutil.copy2 to preserve timestamps when moving to final location
        shutil.copy2(temp_path, file_path)
        logger.debug(f"Copied temporary file to final location: {file_path}")
        
        # Clean up temporary file
        temp_path.unlink()
        logger.debug("Cleaned up temporary file")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        raise 