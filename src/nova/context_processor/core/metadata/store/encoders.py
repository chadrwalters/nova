"""JSON encoders for metadata store."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for metadata objects."""

    def default(self, obj: Any) -> Any:
        """Convert object to JSON serializable type.

        Args:
            obj: Object to convert

        Returns:
            JSON serializable object
        """
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj) 