from typing import List, Optional
from pydantic import BaseModel

class BaseMetadata(BaseModel):
    """Base metadata model."""

    file_path: str
    file_name: str
    file_type: str
    file_size: int
    file_hash: str
    created_at: float
    modified_at: float
    line_count: Optional[int] = None
    word_count: Optional[int] = None
    sheet_count: Optional[int] = None
    links: Optional[List[str]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    color_space: Optional[str] = None
    has_alpha: Optional[bool] = None
    dpi: Optional[int] = None 