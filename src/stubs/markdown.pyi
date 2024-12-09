from typing import List, Optional, overload

@overload
def markdown(text: str) -> str: ...
@overload
def markdown(
    text: str,
    *,
    extensions: Optional[List[str]] = None,
    output_format: Optional[str] = None,
) -> str: ...
