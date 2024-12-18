from pathlib import Path
from typing import Optional, Union
import os
from .logging import get_logger
from .errors import ValidationError

logger = get_logger(__name__)

def resolve_path(
    path: Union[str, Path], 
    base_path: Optional[Path] = None,
    expand_vars: bool = True
) -> Path:
    """
    Resolve a path with consistent rules.
    Args:
        path: Path to resolve
        base_path: Base path for relative paths
        expand_vars: Whether to expand environment variables
    Returns:
        Resolved Path object
    """
    try:
        # Convert to Path if string
        path = Path(path)
        
        # Expand environment variables if requested
        if expand_vars and isinstance(path, Path):
            path = Path(os.path.expandvars(str(path)))
            
        # Handle relative paths
        if base_path and not path.is_absolute():
            path = base_path / path
            
        # Resolve to absolute path
        return path.resolve()
        
    except Exception as e:
        logger.error("path_resolution_failed",
                    path=str(path),
                    base_path=str(base_path) if base_path else None,
                    error=str(e))
        raise ValidationError(f"Failed to resolve path {path}: {str(e)}")

def get_nova_paths() -> dict[str, Path]:
    """Get standard Nova paths from environment."""
    try:
        base_dir = os.environ.get('NOVA_BASE_DIR')
        input_dir = os.environ.get('NOVA_INPUT_DIR')
        processing_dir = os.environ.get('NOVA_PROCESSING_DIR')
        
        if not all([base_dir, input_dir, processing_dir]):
            raise ValidationError("Missing required environment variables")
            
        return {
            'base': resolve_path(base_dir),
            'input': resolve_path(input_dir),
            'processing': resolve_path(processing_dir),
            'markdown_parse': resolve_path(processing_dir) / "01_markdown_parse",
            'markdown_consolidate': resolve_path(processing_dir) / "02_markdown_consolidate",
            'pdf_generate': resolve_path(processing_dir) / "03_pdf_generate"
        }
    except Exception as e:
        logger.error("nova_paths_resolution_failed", error=str(e))
        raise ValidationError(f"Failed to resolve Nova paths: {str(e)}") 