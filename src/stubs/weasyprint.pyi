"""Type stubs for WeasyPrint library."""

from pathlib import Path
from typing import Any, List, Optional, Union

class CSS:
    """CSS stylesheet class."""

    def __init__(
        self,
        filename: Optional[str] = None,
        string: Optional[str] = None,
        url: Optional[str] = None,
        media_type: str = "print",
        font_config: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...

class HTML:
    """HTML document class."""

    def __init__(
        self,
        filename: Optional[str] = None,
        string: Optional[str] = None,
        url: Optional[str] = None,
        base_url: Optional[str] = None,
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> None: ...
    def write_pdf(
        self,
        target: Union[str, Path, Any],
        stylesheets: Optional[List[CSS]] = None,
        zoom: float = 1,
        attachments: Optional[List[Any]] = None,
        font_config: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    def render(
        self,
        stylesheets: Optional[List[CSS]] = None,
        enable_hinting: bool = False,
        **kwargs: Any,
    ) -> Any: ...
