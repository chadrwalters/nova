"""Document converter class."""
from pathlib import Path
from typing import cast, Any, Union, BinaryIO

import html2text  # type: ignore
import pypandoc  # type: ignore
import pdfplumber  # type: ignore
from openpyxl import load_workbook  # type: ignore
from pptx import Presentation  # type: ignore
from pptx.shapes.base import BaseShape  # type: ignore

from .datamodel import Document, InputFormat

class DocumentConverter:
    """Converts documents between formats."""

    def __init__(self) -> None:
        """Initialize the converter."""
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = True
        self._html2text.ignore_images = True
        self._html2text.ignore_tables = False
        self._html2text.body_width = 0

    def convert(self, doc: Document) -> Document:
        """Convert a document to markdown format."""
        if doc.format in (InputFormat.MD, InputFormat.TEXT):
            # Text files are already in a markdown-compatible format
            return Document(content=doc.content, format=InputFormat.MD)

        content = doc.content
        fmt = doc.format

        if fmt == InputFormat.HTML:
            content = cast(str, self._html2text.handle(content))
        elif fmt in (InputFormat.RST, InputFormat.ASCIIDOC, InputFormat.LATEX):
            content = cast(str, pypandoc.convert_text(content, "markdown", format=str(fmt)))
        else:
            raise ValueError(f"Unsupported conversion from {fmt} to markdown")

        return Document(content=content, format=InputFormat.MD)

    def convert_file(self, file_path: Path, fmt: InputFormat) -> Document:
        """Convert a file to markdown format."""
        if fmt in (InputFormat.MD, InputFormat.TEXT):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Document(content=content, format=InputFormat.MD)

        if fmt == InputFormat.HTML:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = cast(str, self._html2text.handle(content))
            return Document(content=content, format=InputFormat.MD)

        if fmt == InputFormat.PDF:
            with pdfplumber.open(file_path) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                content = "\n\n".join(pages)
            return Document(content=content, format=InputFormat.MD)

        if fmt == InputFormat.DOCX:
            content = cast(str, pypandoc.convert_file(str(file_path), "markdown"))
            return Document(content=content, format=InputFormat.MD)

        if fmt == InputFormat.XLSX:
            wb = load_workbook(filename=file_path)
            sheets = []
            for sheet in wb.worksheets:
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    rows.append(" | ".join(str(cell) if cell is not None else "" for cell in row))
                if rows:
                    sheets.append(f"## {sheet.title}\n\n" + "\n".join(rows))
            content = "\n\n".join(sheets)
            return Document(content=content, format=InputFormat.MD)

        if fmt == InputFormat.PPTX:
            prs = Presentation(str(file_path))
            slides = []
            for i, slide in enumerate(prs.slides, 1):
                texts = []
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text = getattr(shape, "text", "")
                        if text:
                            texts.append(text)
                if texts:
                    slides.append(f"## Slide {i}\n\n" + "\n\n".join(texts))
            content = "\n\n".join(slides)
            return Document(content=content, format=InputFormat.MD)

        if fmt in (InputFormat.RST, InputFormat.ASCIIDOC, InputFormat.LATEX):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = cast(str, pypandoc.convert_text(content, "markdown", format=str(fmt)))
            return Document(content=content, format=InputFormat.MD)

        raise ValueError(f"Unsupported conversion from {fmt} to markdown")
