"""Type stubs for python-pptx library."""
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

class Presentation:
    """PowerPoint presentation class."""
    slides: "SlideCollection"
    def __init__(self, pptx: Optional[str] = None) -> None: ...
    def save(self, file: str) -> None: ...

class SlideCollection:
    """Collection of slides."""
    def __iter__(self) -> Iterator["Slide"]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, idx: int) -> "Slide": ...
    def add_slide(self, layout: "SlideLayout") -> "Slide": ...

class Slide:
    """Slide in presentation."""
    shapes: "ShapeCollection"
    placeholders: "ShapeCollection"
    slide_layout: "SlideLayout"
    def get_slide_number(self) -> int: ...

class ShapeCollection:
    """Collection of shapes."""
    def __iter__(self) -> Iterator["Shape"]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, idx: int) -> "Shape": ...
    def add_picture(
        self,
        image_file: str,
        left: int,
        top: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Picture": ...
    def add_textbox(self, left: int, top: int, width: int, height: int) -> "Shape": ...

class Shape:
    """Shape in slide."""
    text: str
    text_frame: "TextFrame"
    def get_or_add_text_frame(self) -> "TextFrame": ...

class TextFrame:
    """Text frame in shape."""
    text: str
    paragraphs: List["Paragraph"]
    def add_paragraph(self) -> "Paragraph": ...
    def clear(self) -> None: ...

class Paragraph:
    """Paragraph in text frame."""
    text: str
    runs: List["Run"]
    def add_run(self) -> "Run": ...

class Run:
    """Run in paragraph."""
    text: str
    font: "Font"

class Font:
    """Font properties."""
    name: str
    size: int
    bold: bool
    italic: bool
    underline: bool
    color: Any

class SlideLayout:
    """Slide layout."""
    name: str
    placeholders: "ShapeCollection"

class Picture(Shape):
    """Picture shape."""
    def get_image(self) -> Any: ... 