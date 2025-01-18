"""Test document converter functionality."""

import json
from pathlib import Path
from typing import Generator
from PIL import Image, ImageDraw, ExifTags, PngImagePlugin
import pytest
import xml.etree.ElementTree as ET
import piexif
import piexif.helper

from nova.docling.document_converter import DocumentConverter, _convert_image_to_markdown, _convert_svg_to_markdown


@pytest.fixture
def test_files(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test files in various formats."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()

    # Create test PNG with metadata
    png_file = test_dir / "test.png"
    img = Image.new('RGB', (100, 100), color='red')
    img.info['gamma'] = 2.2
    img.info['srgb'] = 1
    img.info['comment'] = "Test comment"
    # Save with pnginfo to preserve metadata
    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text('gamma', str(img.info['gamma']))
    pnginfo.add_text('srgb', str(img.info['srgb']))
    pnginfo.add_text('comment', img.info['comment'])
    img.save(png_file, format='PNG', pnginfo=pnginfo)

    # Create test JPEG with EXIF data
    jpeg_file = test_dir / "test.jpg"
    img = Image.new('RGB', (100, 100), color='blue')

    # Create EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Test Camera",
            piexif.ImageIFD.Model: "Test Model",
            piexif.ImageIFD.DateTime: "2024:01:15 12:00:00"
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(jpeg_file, format='JPEG', exif=exif_bytes)

    # Create test WebP
    webp_file = test_dir / "test.webp"
    img = Image.new('RGB', (100, 100), color='green')
    # Set WebP-specific parameters
    img.save(webp_file, format='WEBP', lossless=True, quality=100, method=6)

    # Create test SVG
    svg_file = test_dir / "test.svg"
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100" height="100" viewBox="0 0 100 100">
  <title>Test SVG</title>
  <desc>Test description</desc>
  <rect x="10" y="10" width="80" height="80" fill="blue"/>
  <circle cx="50" cy="50" r="30" fill="red"/>
</svg>'''
    svg_file.write_text(svg_content)

    yield test_dir


def test_png_metadata(test_files: Path) -> None:
    """Test PNG metadata handling."""
    png_file = test_files / "test.png"
    converter = DocumentConverter()

    # Convert PNG to markdown
    doc = converter.convert(png_file)
    assert doc.metadata is not None

    # Check metadata format
    assert "png_gamma" in doc.metadata
    assert float(doc.metadata["png_gamma"]) == 2.2
    assert "png_srgb" in doc.metadata
    assert int(doc.metadata["png_srgb"]) == 1
    assert "png_comment" in doc.metadata
    assert doc.metadata["png_comment"] == "Test comment"


def test_jpeg_exif_data(test_files: Path) -> None:
    """Test JPEG EXIF data extraction."""
    jpeg_file = test_files / "test.jpg"
    converter = DocumentConverter()

    # Convert JPEG to markdown
    doc = converter.convert(jpeg_file)
    assert doc.metadata is not None

    # Check EXIF data
    assert "exif_Make" in doc.metadata
    assert doc.metadata["exif_Make"] == "Test Camera"
    assert "exif_Model" in doc.metadata
    assert doc.metadata["exif_Model"] == "Test Model"
    assert "exif_DateTime" in doc.metadata
    assert doc.metadata["exif_DateTime"] == "2024:01:15 12:00:00"


def test_webp_metadata(test_files: Path) -> None:
    """Test WebP metadata handling."""
    webp_file = test_files / "test.webp"
    converter = DocumentConverter()

    # Convert WebP to markdown
    doc = converter.convert(webp_file)
    assert doc.metadata is not None

    # Check WebP metadata
    assert "webp_lossless" in doc.metadata
    assert doc.metadata["webp_lossless"] == "True"
    assert "webp_quality" in doc.metadata
    assert doc.metadata["webp_quality"] == "100"


def test_svg_path_handling(test_files: Path) -> None:
    """Test SVG path handling."""
    svg_file = test_files / "test.svg"
    converter = DocumentConverter()

    # Convert SVG to markdown
    doc = converter.convert(svg_file)
    assert doc.metadata is not None

    # Check SVG metadata
    assert "xmlns" in doc.metadata
    assert doc.metadata["xmlns"] == "http://www.w3.org/2000/svg"
    assert "version" in doc.metadata
    assert doc.metadata["version"] == "1.1"
    assert "width" in doc.metadata
    assert doc.metadata["width"] == "100"
    assert "height" in doc.metadata
    assert doc.metadata["height"] == "100"
    assert "viewBox" in doc.metadata
    assert doc.metadata["viewBox"] == "0 0 100 100"
    assert "title" in doc.metadata
    assert doc.metadata["title"] == "Test SVG"
    assert "description" in doc.metadata
    assert doc.metadata["description"] == "Test description"

    # Check element counts
    element_counts = json.loads(doc.metadata["element_counts"])
    assert element_counts["rect"] == 1
    assert element_counts["circle"] == 1
