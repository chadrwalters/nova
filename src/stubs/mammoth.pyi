"""Type stubs for mammoth library."""

from typing import Any, BinaryIO, Dict, List, Optional, Union

class Result:
    """Result of document conversion."""

    value: str
    messages: List[Dict[str, Any]]

def convert_to_html(
    input_file: Union[str, BinaryIO],
    style_map: Optional[str] = None,
    transform_document: Optional[Any] = None,
    convert_image: Optional[Any] = None,
    embed_style_map: Optional[str] = None,
    ignore_empty_paragraphs: bool = True,
    **kwargs: Any,
) -> Result: ...
def convert_to_markdown(
    input_file: Union[str, BinaryIO],
    style_map: Optional[str] = None,
    transform_document: Optional[Any] = None,
    convert_image: Optional[Any] = None,
    **kwargs: Any,
) -> Result: ...
