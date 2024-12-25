---
title: Complex Test Document
author: Test User
date: 2024-01-01
tags: [test, markdown, complex]
---

# Complex Document Example

## Overview

This document combines various markdown elements to test parser robustness.

### Code Samples

Here's a Python code block:

```python
def process_markdown(content):
    """Process markdown content."""
    result = []
    for line in content.split('\n'):
        result.append(line.strip())
    return '\n'.join(result)
```

And some inline `code` elements.

### Images and Links

Here's our architecture diagram:
![Architecture Overview](../attachments/png_test.png "System Architecture")

Related documents:
- [Implementation Guide](../attachments/pdf_test.pdf)
- [API Documentation](https://api.example.com)

### Mixed Content Lists

1. First Major Point
   - Sub-point with *italic* text
   - Sub-point with **bold** text
   - Sub-point with `code`
   ![Diagram](../attachments/png_test.png)

2. Second Major Point
   > Important quote that
   > spans multiple lines
   > with [a link](https://example.com)

### Tables and Formatting

| Feature | Status | Notes |
|---------|--------|-------|
| Parsing | ✅ | Basic functionality |
| Images | ⚠️ | Needs processing |
| Links | ✅ | Fully supported |

## Technical Details

```json
{
  "version": "1.0",
  "settings": {
    "enabled": true,
    "mode": "strict"
  }
}
```

### Final Notes

Last image reference: ![Final](../attachments/jpg_test.jpg)

---
references:
  - type: image
    count: 3
  - type: code_block
    count: 2
  - type: table
    count: 1 