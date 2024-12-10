"""Type stubs for BeautifulSoup library."""

from typing import Any, Dict, Iterator, List, Optional, Union

class Tag:
    """HTML tag class."""

    name: str
    attrs: Dict[str, Any]
    contents: List[Any]
    parent: Optional["Tag"]
    string: Optional[str]

    def get(self, key: str, default: Any = None) -> Any: ...
    def get_text(self, separator: str = "", strip: bool = False) -> str: ...
    def find_all(
        self,
        name: Optional[str] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        text: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> List["Tag"]: ...
    def find(
        self,
        name: Optional[str] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        text: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional["Tag"]: ...
    def decompose(self) -> None: ...
    def replace_with(self, replace_with: Union[str, "Tag"]) -> "Tag": ...

class BeautifulSoup(Tag):
    """BeautifulSoup class for parsing HTML/XML."""

    def __init__(
        self,
        markup: str = "",
        features: Optional[str] = None,
        builder: Optional[Any] = None,
        parse_only: Optional[Any] = None,
        from_encoding: Optional[str] = None,
        exclude_encodings: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None: ...
    def new_tag(
        self,
        name: str,
        namespace: Optional[str] = None,
        nsprefix: Optional[str] = None,
        attrs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tag: ...
    def get_text(self, separator: str = "", strip: bool = False) -> str: ...
    def prettify(self, encoding: Optional[str] = None) -> str: ...
