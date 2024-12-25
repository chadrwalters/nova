# Nova Document Processor Architecture

## System Overview

Nova is a document processing pipeline designed to handle markdown files with embedded content, consolidate them, and produce organized output. The system follows a phase-based architecture where each phase performs specific transformations on the input data.

## Core Components

### 1. Pipeline Phases
- **MARKDOWN_PARSE**: Initial parsing and processing of markdown files
- **MARKDOWN_CONSOLIDATE**: Consolidation of markdown files with attachments
- **MARKDOWN_AGGREGATE**: Aggregation into a single file
- **MARKDOWN_SPLIT_THREEFILES**: Final split into summary, raw notes, and attachments

### 2. Key Technologies
- Python 3.9+
- Poetry for dependency management
- OpenAI GPT-4 Vision for image description
- Custom markdown processing (markitdown)

### 3. Data Flow
1. Input markdown files → MARKDOWN_PARSE
2. Processed files → MARKDOWN_CONSOLIDATE
3. Consolidated files → MARKDOWN_AGGREGATE
4. Aggregated file → MARKDOWN_SPLIT_THREEFILES
5. Final output: summary.md, raw_notes.md, attachments.md

## Integration Points

### External Services
- OpenAI API for image description generation
- File system for document storage and processing
- Environment variables for configuration

### Internal Components
- Core handlers for file processing
- Utility functions for common operations
- State management for tracking progress
- Resource management for efficient processing

## Technical Stack

### Core Libraries
- markitdown==0.0.1a3: Custom markdown processing
- Python standard library: File operations
- OpenAI API: Image processing
- Poetry: Dependency management

### Development Tools
- pytest: Testing framework
- mypy: Type checking
- Poetry: Package management

## Performance Considerations

### Resource Management
- Image processing limits
- Memory management for large files
- Disk space optimization
- Cache management

### Scalability
- Phase-based processing for modularity
- Independent component processing
- Configurable resource limits
- State tracking for recovery 