"""Serialization utilities for Nova."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class NovaJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Nova objects."""
    
    def default(self, obj):
        """Handle custom object serialization.
        
        Args:
            obj: Object to serialize.
            
        Returns:
            JSON-serializable object.
        """
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def serialize_metadata(obj: Dict[str, Any]) -> str:
    """Serialize metadata to JSON string.
    
    Args:
        obj: Metadata dictionary.
        
    Returns:
        JSON string.
    """
    return json.dumps(obj, cls=NovaJSONEncoder, indent=2)


def deserialize_metadata(data: str) -> Dict[str, Any]:
    """Deserialize metadata from JSON string.
    
    Args:
        data: JSON string.
        
    Returns:
        Metadata dictionary.
    """
    return json.loads(data) 