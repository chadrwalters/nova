"""Type stubs for python-magic library."""

from typing import Any, Optional, Union

def from_file(filename: str, mime: bool = False) -> str: ...
def from_buffer(buffer: Union[bytes, str], mime: bool = False) -> str: ...

class Magic:
    """Magic class for file type detection."""

    def __init__(
        self,
        mime: bool = False,
        magic_file: Optional[str] = None,
        mime_encoding: bool = False,
        keep_going: bool = False,
        uncompress: bool = False,
        **kwargs: Any,
    ) -> None: ...
    def from_file(self, filename: str) -> str: ...
    def from_buffer(self, buffer: Union[bytes, str]) -> str: ...
    def close(self) -> None: ...
