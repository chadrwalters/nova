"""Type stubs for markdown library."""

from typing import Any, Dict, List, Optional, Type, Union

class Extension:
    """Base class for markdown extensions."""

    def extendMarkdown(self, md: "Markdown") -> None: ...

class Markdown:
    """Markdown processor class."""

    parser: Any
    output_formats: Dict[str, Any]
    preprocessors: Dict[str, Any]
    block_processors: Dict[str, Any]
    treeprocessors: Dict[str, Any]
    postprocessors: Dict[str, Any]
    inlinepatterns: Dict[str, Any]
    htmlStash: Any
    references: Dict[str, Any]
    def __init__(
        self,
        extensions: Optional[List[Union[str, Extension]]] = None,
        extension_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        output_format: str = "xhtml",
        tab_length: int = 4,
    ) -> None: ...
    def convert(self, source: str) -> str: ...
    def reset(self) -> None: ...
    def registerExtension(self, extension: Extension) -> None: ...
    def build_parser(self) -> None: ...
    def build_block_parser(self) -> None: ...
    def build_inline_parser(self) -> None: ...
    def convert_to_html(self, source: str) -> str: ...

def markdown(
    text: str,
    extensions: Optional[List[Union[str, Extension]]] = None,
    extension_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    output_format: str = "xhtml",
    tab_length: int = 4,
) -> str: ...
