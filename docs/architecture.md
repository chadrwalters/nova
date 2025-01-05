# Nova Architecture

## Overview

Nova is a document processing system that transforms various document formats into structured markdown with metadata.

## Development Standards

### Code Quality Tools

The project enforces code quality through automated tools:

1. **Code Formatting**
   - Black for consistent Python formatting
   - Line length: 88 characters
   - Automatic formatting on commit

2. **Import Management**
   - isort with black profile
   - Consistent import grouping and ordering
   - Automatic sorting on commit

3. **Code Analysis**
   - flake8 for style guide enforcement
   - mypy for static type checking
   - bandit for security analysis

4. **Version Control**
   - Commitizen for standardized commit messages
   - Conventional commits format
   - Automated validation on commit

These tools are enforced through pre-commit hooks, ensuring consistent code quality across all contributions.

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

The system processes documents through multiple phases, each with specific responsibilities and boundaries:

#### 1. Parse Phase
**Responsibility**: Convert input documents from various formats into standardized markdown
- **Input Location**: `input_dir` (User's input directory)
- **Input Files**: Any supported document type (PDF, DOCX, MD, Images, etc.)
- **Output Location**: `processing_dir/phases/parse`
- **Output Files**: `{filename}.parsed.md` for each input file
- **State Management**: Tracks processed files, errors, and file type statistics

#### 2. Disassemble Phase
**Responsibility**: Split parsed markdown files into summary and raw notes sections
- **Input Location**: `processing_dir/phases/parse`
- **Input Files**: `*.parsed.md` files from Parse Phase
- **Output Location**: `processing_dir/phases/disassemble`
- **Output Files**: 
  - `{filename}.summary.md`: Contains content before the `--==RAW NOTES==--` marker
  - `{filename}.rawnotes.md`: Contains content after the marker
- **State Management**: Tracks split statistics and section counts

#### 3. Split Phase
**Responsibility**: Organize and consolidate disassembled files into core document structure
- **Input Location**: `processing_dir/phases/disassemble`
- **Input Files**: 
  - `*.summary.md` files
  - `*.rawnotes.md` files
  - Any attachments referenced in the content
- **Output Location**: `processing_dir/phases/split`
- **Output Files**:
  - `Summary.md`: Consolidated summary content
  - `Raw Notes.md`: Consolidated raw notes
  - `Attachments.md`: Organized attachment references and metadata
- **State Management**: Tracks file consolidation and attachment organization

#### 4. Finalize Phase
**Responsibility**: Generate final output with complete metadata and structure
- **Input Location**: `processing_dir/phases/split`
- **Input Files**: The three core files (Summary, Raw Notes, Attachments)
- **Output Location**: `output_dir`
- **Output Files**: 
  - Final document structure with metadata
  - Table of contents
  - Cross-referenced attachments
  - Metadata files
- **State Management**: Tracks output generation and metadata completion

### Document Handlers

Specialized handlers process different document types:
- PDF documents (using pypdf)
- Word documents (using python-docx)
- Markdown files
- Images (with OpenAI Vision API)
- Text files
- Spreadsheets (using openpyxl)
- HTML files

Each handler implements a common interface and provides:
- File type detection
- Content extraction
- Metadata parsing
- Format conversion
- Error handling

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

### Testing

The test suite is organized into several categories:
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Handler-specific tests for each document type
- Configuration tests
- Utility function tests

Test configuration is managed through `pytest.ini` with:
- Custom markers for test categorization
- Async test support with pytest-asyncio
- Detailed logging configuration
- Mock filesystem support

## Development Guidelines

See [Development Guidelines](development.md) for coding standards and practices.