# Nova Architecture

## Overview

Nova is a document processing system that transforms various document formats into structured markdown with metadata.

## Core Components

### Configuration Management

The configuration system uses a layered approach:

1. Default configuration (`src/nova/config/default.yaml`)
2. User configuration (`config/nova.yaml`)

Configuration values are loaded in this order, with user config overriding defaults.

#### Configuration Files

The configuration files use YAML format and support:
- Path variables using `base_dir` reference
- User home directory expansion (`~`)
- Nested configuration sections

Example configuration:
```yaml
base_dir: ~/nova
input_dir: ~/nova/input
output_dir: ~/nova/output

apis:
  openai:
    api_key: "your-api-key-here"
```

#### Configuration Loading

1. Load default configuration
2. Load user configuration
3. Merge configurations (user overrides default)
4. Expand paths (~ for home directory)
5. Validate required fields
6. Create required directories

### Document Processing

The system processes documents through multiple phases:

1. Parse - Convert documents to markdown
2. Disassemble - Split into summary and notes
3. Split - Organize into sections
4. Finalize - Generate output with metadata

### Document Handlers

Specialized handlers process different document types:
- PDF documents
- Word documents (DOCX)
- Markdown files
- Images (with AI vision)
- Text files
- Spreadsheets
- HTML files

### Pipeline Management

The pipeline orchestrates document processing:
1. Identify document type
2. Select appropriate handler
3. Execute processing phases
4. Track progress and errors
5. Generate output files

### Logging and Debugging

Comprehensive logging system with:
- Multiple log levels (ERROR, WARNING, INFO, DEBUG)
- Phase-specific logging
- Performance tracking
- Error reporting

## Development Guidelines

See [Development Guidelines](development.md) for coding standards and practices.