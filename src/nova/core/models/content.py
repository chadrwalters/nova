"""Document and content models."""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class Document(BaseModel):
    """Document model for processing pipeline."""
    
    path: Path
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    attachments: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize Document."""
        if 'metadata' not in data:
            data['metadata'] = {}
        if 'attachments' not in data:
            data['attachments'] = {}
        super().__init__(**data)
        
    def model_dump(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'path': str(self.path),
            'content': self.content,
            'metadata': self.metadata,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        } 