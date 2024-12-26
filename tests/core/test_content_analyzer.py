"""Tests for the ContentAnalyzer class."""

import pytest
from nova.core.content_analyzer import ContentAnalyzer, ContentType

@pytest.fixture
def analyzer():
    """Create a ContentAnalyzer instance."""
    return ContentAnalyzer()

def test_empty_content(analyzer):
    """Test analyzing empty content."""
    result = analyzer.analyze_content("")
    assert result['content_type'] == ContentType.RAW_NOTE
    assert result['confidence'] == 1.0
    assert not any(result['characteristics'].values())

def test_summary_content(analyzer):
    """Test analyzing summary-like content."""
    content = """# Main Heading
    
**Key Points**:
- Important point 1
- Important point 2

> Important quote
"""
    result = analyzer.analyze_content(content)
    assert result['content_type'] == ContentType.SUMMARY
    assert result['confidence'] > 0.5
    assert result['characteristics']['structure_level'] > 0

def test_technical_content(analyzer):
    """Test analyzing technical content."""
    content = """Here's some code:
    
```python
def hello():
    print("Hello World")
```

And a table:
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

IP: 192.168.1.1
Size: 128MB
"""
    result = analyzer.analyze_content(content)
    assert result['content_type'] == ContentType.TECHNICAL
    assert result['confidence'] > 0.5
    assert result['characteristics']['has_code']
    assert result['characteristics']['technical_density'] > 0

def test_reference_content(analyzer):
    """Test analyzing reference content."""
    content = """References:
1. First reference
2. Second reference

[link1]: http://example.com
[link2]: http://example.org

See also:
- Related topic 1
- Related topic 2
"""
    result = analyzer.analyze_content(content)
    assert result['content_type'] == ContentType.REFERENCE
    assert result['confidence'] > 0.5

def test_attachment_content(analyzer):
    """Test analyzing content with attachments."""
    content = """Here are some attachments:

![Image 1](image1.png)
![Image 2](image2.jpg)

[Document 1](document1.pdf)
[Document 2](document2.docx)

--==ATTACHMENT_BLOCK: file.pdf==--
Content
--==ATTACHMENT_BLOCK_END==--
"""
    result = analyzer.analyze_content(content)
    assert result['content_type'] == ContentType.ATTACHMENT
    assert result['confidence'] > 0.5
    assert result['characteristics']['has_images']
    assert result['characteristics']['has_links']

def test_mixed_content(analyzer):
    """Test analyzing mixed content."""
    content = """# Section with Code

```python
print("Hello")
```

![Image](image.png)

Regular text paragraph.
"""
    result = analyzer.analyze_content(content)
    # Mixed content should be classified based on dominant type
    assert result['characteristics']['has_code']
    assert result['characteristics']['has_images']
    assert result['characteristics']['structure_level'] > 0

def test_section_suggestions(analyzer):
    """Test section suggestions for different content types."""
    # Test summary content
    summary_content = "# Main Points\n**Key Points**:\n- Point 1\n- Point 2"
    section, confidence = analyzer.suggest_section(summary_content)
    assert section == 'summary'
    assert confidence > 0.5
    
    # Test technical content
    technical_content = "```python\nprint('hello')\n```"
    section, confidence = analyzer.suggest_section(technical_content)
    assert section == 'raw_notes'
    assert confidence > 0.5
    
    # Test attachment content
    attachment_content = "![Image](image.png)\n[Doc](file.pdf)"
    section, confidence = analyzer.suggest_section(attachment_content)
    assert section == 'attachments'
    assert confidence > 0.5 