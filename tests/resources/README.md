# Nova Test Resources

This directory contains test files used by Nova's test suite. The files are minimal examples designed to test specific functionality without adding unnecessary complexity.

## Directory Structure

```
resources/
├── markdown/
│   ├── simple.md           # Basic markdown with common formatting
│   └── with_images.md      # Markdown with image references
├── documents/
│   ├── sample.pdf          # Simple PDF with text and formatting
│   └── create_test_pdf.py  # Script to generate test PDF
└── images/
    ├── test.jpg           # Test image with shapes and text
    ├── test.png           # PNG version of test image
    └── create_test_image.py # Script to generate test images
```

## File Descriptions

### Markdown Files
- `simple.md`: Tests basic markdown parsing with common elements like headers, lists, code blocks, and basic formatting.
- `with_images.md`: Tests image handling with various reference styles and formats.

### Documents
- `sample.pdf`: A simple PDF file containing formatted text and basic layout elements.
- `create_test_pdf.py`: Python script using reportlab to generate the test PDF.

### Images
- `test.jpg`: A JPEG image with basic shapes and text.
- `test.png`: PNG version of the test image for format comparison.
- `create_test_image.py`: Python script using Pillow to generate test images.

## Usage

These test files are used by various test cases in the Nova test suite. They are designed to be:
1. Small and focused
2. Easy to regenerate
3. Consistent across test runs

### Regenerating Test Files

To regenerate test files:

```bash
cd tests/resources/documents
python create_test_pdf.py

cd ../images
python create_test_image.py
```

## Dependencies

The test file generation scripts require:
- reportlab (for PDF generation)
- Pillow (for image generation)

Install with:
```bash
pip install reportlab pillow
``` 