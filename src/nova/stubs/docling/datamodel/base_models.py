"""Type stubs for docling.datamodel.base_models module."""

from enum import Enum


class InputFormat(str, Enum):
    """A document format supported by document backend parsers."""

    DOCX = "docx"
    PPTX = "pptx"
    HTML = "html"
    XML_PUBMED = "xml_pubmed"
    IMAGE = "image"
    PDF = "pdf"
    ASCIIDOC = "asciidoc"
    MD = "md"
    XLSX = "xlsx"
    XML_USPTO = "xml_uspto"
