# Processing Examples

This document provides examples of using the Nova document processing pipeline for various common scenarios.

## Basic Usage

### Simple Document Processing
```python
from pathlib import Path
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

# Create processor
processor = ThreeFileSplitProcessor()

# Set up output files
output_files = {
    'summary': Path('output/summary.md'),
    'raw_notes': Path('output/raw_notes.md'),
    'attachments': Path('output/attachments.md')
}

# Example content
content = """
# Project Meeting Notes

Key decisions from today's meeting.

--==ATTACHMENT_BLOCK: agenda.txt==--
1. Project status
2. Timeline review
3. Next steps
--==ATTACHMENT_BLOCK_END==--

## Discussion Points
Detailed discussion notes...
"""

# Process content
metrics = processor.process(content, output_files)
print(f"Processing complete. Distribution: {metrics['distribution']}")
```

### Batch Processing
```python
import concurrent.futures
from pathlib import Path

def process_file(file_path: Path, output_dir: Path) -> dict:
    """Process a single file."""
    processor = ThreeFileSplitProcessor()
    
    # Set up output files
    output_files = {
        'summary': output_dir / f"{file_path.stem}_summary.md",
        'raw_notes': output_dir / f"{file_path.stem}_raw_notes.md",
        'attachments': output_dir / f"{file_path.stem}_attachments.md"
    }
    
    # Read and process content
    content = file_path.read_text()
    return processor.process(content, output_files)

# Process multiple files concurrently
input_dir = Path('input')
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = []
    for file_path in input_dir.glob('*.md'):
        future = executor.submit(process_file, file_path, output_dir)
        futures.append(future)
    
    # Wait for all tasks to complete
    results = [f.result() for f in futures]
```

## Content Examples

### Document with Metadata
```markdown
---
title: Project Overview
author: John Doe
date: 2024-01-01
tags: [project, documentation]
---

# Project Overview

Executive summary...

--==ATTACHMENT_BLOCK: timeline.txt==--
Q1: Planning
Q2: Development
Q3: Testing
Q4: Deployment
--==ATTACHMENT_BLOCK_END==--
```

### Cross-Referenced Content
```markdown
# Main Document

See [[Technical Details]] for implementation notes.

--==ATTACHMENT_BLOCK: overview.txt==--
High-level system overview.
References [[Architecture]] for details.
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: technical.txt==--
This is the Technical Details section.
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: architecture.txt==--
System architecture details.
--==ATTACHMENT_BLOCK_END==--
```

### Navigation Links
```markdown
<!-- prev: introduction.md -->
<!-- next: implementation.md -->
<!-- parent: index.md -->

# Design Document

Design principles and guidelines...

--==ATTACHMENT_BLOCK: diagrams.txt==--
System component diagrams...
--==ATTACHMENT_BLOCK_END==--
```

## Advanced Usage

### Custom Content Distribution
```python
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

class CustomSplitProcessor(ThreeFileSplitProcessor):
    """Custom processor with modified content distribution."""
    
    def _split_content(self, content: str) -> tuple[str, str]:
        """Override split logic."""
        lines = content.split('\n')
        summary_lines = []
        raw_notes_lines = []
        
        # Custom splitting logic
        in_summary = True
        for line in lines:
            if line.startswith('## Details'):
                in_summary = False
            
            if in_summary:
                summary_lines.append(line)
            else:
                raw_notes_lines.append(line)
        
        return '\n'.join(summary_lines), '\n'.join(raw_notes_lines)

# Use custom processor
processor = CustomSplitProcessor()
metrics = processor.process(content, output_files)
```

### Performance Monitoring
```python
import time
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

# Create processor
processor = ThreeFileSplitProcessor()

# Process with performance monitoring
start_time = time.time()
metrics = processor.process(content, output_files)

# Analyze metrics
print(f"Processing time: {metrics['processing_time']:.2f}s")
print(f"Memory usage: {metrics['memory_usage'] / 1024 / 1024:.1f}MB")
print("Content distribution:")
for file_type, percentage in metrics['distribution'].items():
    print(f"- {file_type}: {percentage:.1f}%")
```

### Error Handling
```python
from nova.core.errors import ProcessingError
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor

processor = ThreeFileSplitProcessor()

try:
    metrics = processor.process(content, output_files)
except ProcessingError as e:
    if "Unclosed attachment block" in str(e):
        print("Error: Found unclosed attachment block")
        print("Please check attachment markers")
    elif "Duplicate reference target" in str(e):
        print("Error: Found duplicate reference")
        print("Please ensure reference names are unique")
    else:
        print(f"Processing error: {e}")
```

## Output Examples

### Summary File (summary.md)
```markdown
# Project Overview

Executive summary and key points...

## Key Decisions
1. Decision A
2. Decision B

Navigation:
- [Raw Notes](raw_notes.md)
- [Attachments](attachments.md)
```

### Raw Notes File (raw_notes.md)
```markdown
# Detailed Notes

## Discussion Points
* Point 1
* Point 2

## Action Items
1. Task A
2. Task B

Referenced Files:
- [timeline.txt](attachments.md#timeline)
- [diagrams.txt](attachments.md#diagrams)
```

### Attachments File (attachments.md)
```markdown
# Attachments

<div id="timeline">

## timeline.txt
```text
Q1: Planning
Q2: Development
Q3: Testing
Q4: Deployment
```
</div>

<div id="diagrams">

## diagrams.txt
```text
System component diagrams...
```
</div>
``` 