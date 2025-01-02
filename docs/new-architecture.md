# Nova System Architecture

## Table of Contents
1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Pipeline Architecture](#pipeline-architecture)
4. [Directory Structure](#directory-structure)
5. [Handler System](#handler-system)
6. [Configuration](#configuration)
7. [Error Handling & Logging](#error-handling--logging)
8. [Testing & Validation](#testing--validation)

## Overview

Nova is a document processing pipeline designed to convert various input formats into structured Markdown outputs. The system follows these key principles:

1. **Phase-Based Processing**: Clear separation of concerns through distinct processing phases
2. **Handler-Based Parsing**: Specialized handlers for each file type
3. **Consistent Output**: Standardized Markdown generation across all handlers
4. **Robust Error Handling**: Comprehensive validation and error recovery
5. **Extensible Design**: Easy addition of new handlers and phases

## Core Components

### MarkdownWriter
Central class for generating consistent Markdown output:
```python
class MarkdownWriter:
    def write_section(self, title: str, content: str, level: int = 1) -> str
    def write_metadata(self, metadata: Dict[str, Any]) -> str
    def write_reference(self, ref_type: str, marker: str) -> str
```

### ImageConverter
Unified image conversion handling:
```python
class ImageConverter:
    def convert_to_jpeg(self, source: Path, target: Path) -> Path
    def convert_svg(self, source: Path, target: Path) -> Path
    def convert_heic(self, source: Path, target: Path) -> Path
```

### LoggingManager
Centralized logging configuration:
```python
class LoggingManager:
    def configure(self, level: str, output: str)
    def get_logger(self, name: str) -> Logger
```

### ReprocessingManager
Unified logic for file reprocessing decisions:
```python
class ReprocessingManager:
    def should_reprocess(self, file: Path, phase: str) -> bool
    def register_phase_override(self, phase: str, checker: Callable)
```

## Pipeline Architecture

### Phase Structure
```mermaid
graph LR
    Input[Input Files] --> Parse[Parse Phase]
    Parse --> Disassemble[Disassemble Phase]
    Disassemble --> Split[Split Phase]
    Split --> Finalize[Finalize Phase]
    Finalize --> Output[Output Files]
```

### Phase Responsibilities

1. **Parse Phase**
   - Converts input files to .parsed.md
   - Uses appropriate handler for each file type
   - Generates initial metadata

2. **Disassemble Phase**
   - Splits content into sections
   - Generates summary/notes/attachments
   - Creates reference markers for cross-document links

3. **Split Phase**
   - Consolidates content by type
   - Maintains reference markers
   - Creates final structure

4. **Finalize Phase**
   - Validates output integrity
   - Verifies reference markers exist
   - Generates final output

## Directory Structure

```
nova/
├── src/
│   └── nova/
│       ├── core/
│       │   ├── markdown/
│       │   │   ├── writer.py
│       │   │   └── templates/
│       │   ├── converters/
│       │   │   └── image.py
│       │   └── logging/
│       │       └── manager.py
│       ├── handlers/
│       │   ├── base.py
│       │   ├── document.py
│       │   ├── image.py
│       │   └── markdown.py
│       ├── phases/
│       │   ├── parse.py
│       │   ├── disassemble.py
│       │   ├── split.py
│       │   └── finalize.py
│       └── utils/
│           ├── reprocessing.py
│           └── validation.py
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    └── architecture.md
```

## Handler System

### Base Handler
```python
class BaseHandler:
    def process(self, file_path: Path) -> Optional[DocumentMetadata]
    def write_markdown(self, content: str, metadata: Dict[str, Any])
```

### Handler Registry
```python
class HandlerRegistry:
    def register(self, extensions: List[str], handler_class: Type[BaseHandler])
    def get_handler(self, file_extension: str) -> Optional[BaseHandler]
```

### Standard Handlers
- DocumentHandler: PDF, DOCX
- ImageHandler: JPG, PNG, HEIC, SVG
- MarkdownHandler: MD, TXT
- Additional handlers as needed

## Configuration

### Configuration Structure
```yaml
base_dir: "${HOME}/Documents/Nova"
input_dir: "${HOME}/Documents/Nova/Input"
output_dir: "${HOME}/Documents/Nova/Output"
processing_dir: "${HOME}/Documents/Nova/Processing"

logging:
  level: "INFO"
  file: "nova.log"

handlers:
  image:
    formats: ["jpg", "png", "heic", "svg"]
    converter:
      heic_command: "sips"
      svg_density: 300

pipeline:
  phases: ["parse", "disassemble", "split", "finalize"]
```

### Environment Variables
- NOVA_CONFIG_PATH: Custom config location
- NOVA_LOG_LEVEL: Override logging level
- NOVA_BASE_DIR: Override base directory

## Error Handling & Logging

### Logging Hierarchy
1. Application-level logging (nova.log)
2. Phase-specific logging
3. Handler-specific logging
4. Debug logging (when enabled)

### Error Types
```python
class NovaError(Exception): pass
class ProcessingError(NovaError): pass
class ValidationError(NovaError): pass
class ConfigurationError(NovaError): pass
```

### Validation System
```python
class PipelineValidator:
    def validate_phase(self, phase: str) -> bool
    def validate_output(self) -> bool
    def validate_references(self) -> bool
```

## Testing & Validation

### Test Categories
1. **Unit Tests**
   - Handler tests
   - Phase tests
   - Utility tests

2. **Integration Tests**
   - Full pipeline tests
   - Cross-phase validation
   - Output verification

3. **Performance Tests**
   - Large file handling
   - Memory usage
   - Processing time

### Validation Requirements
- Execute cleanup.sh -a && run_nova.sh
- Compare output with expected results
- Verify all references resolve
- Check performance metrics

### CI/CD Integration
- Automated testing on commits
- Performance regression checks
- Documentation updates
- Version management