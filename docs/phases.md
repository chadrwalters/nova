# Nova Phases

## Overview

Nova processes documents through a series of well-defined phases, each responsible for a specific aspect of document transformation. The phases work together to convert various input formats into a structured, metadata-rich markdown format.

## Phase Architecture

### Base Phase

The `Phase` base class (`src/nova/context_processor/phases/base.py`) provides the foundation for all processing phases with common functionality:

- Metadata management
- File processing status tracking
- Error handling
- Output file management
- Directory processing

### Core Components

#### Phase Lifecycle
Each phase follows a standard lifecycle:
1. Initialization with configuration and pipeline
2. File processing
3. Metadata updates
4. Output generation
5. Finalization (optional)

#### Base Methods

- `process_file`: Processes individual files
- `process_directory`: Handles directory-level processing
- `finalize`: Runs cleanup and finalization steps
- `_update_base_metadata`: Updates core metadata fields

## Processing Phases

### 1. Parse Phase

The `ParsePhase` is the initial processing phase that converts input documents into a common markdown format.

#### Key Features
- File type detection
- Handler selection and initialization
- Initial metadata creation
- Content extraction
- Format conversion

#### Processing Flow
1. Identifies appropriate handler for file type
2. Creates initial metadata
3. Processes file using selected handler
4. Generates parsed markdown output
5. Stores phase-specific metadata

### 2. Disassembly Phase

The `DisassemblyPhase` breaks down parsed documents into logical components.

#### Key Features
- Content normalization
- Section splitting
- Attachment handling
- Size limit enforcement
- Metadata tracking

#### Processing Flow
1. Validates input markdown
2. Splits content at `--==RAW NOTES==--` marker
3. Creates summary and raw notes sections
4. Processes attachments
5. Updates section metadata

#### Content Limits
- Summary content: 1MB limit
- Raw notes content: 5MB limit
- Content exceeding limits is truncated

### 3. Split Phase

The `SplitPhase` organizes content into standardized sections.

#### Key Features
- Section identification
- Content organization
- Metadata enrichment
- Section validation

#### Standard Sections
- Summary
- Details
- Notes
- References

#### Processing Flow
1. Reads parsed content
2. Identifies section markers
3. Distributes content to appropriate sections
4. Creates section-specific files
5. Updates metadata with section information

### 4. Finalize Phase

The `FinalizePhase` completes document processing and prepares final output.

#### Key Features
- Output organization
- File consolidation
- Metadata finalization
- Directory structure creation

#### Processing Flow
1. Creates final directory structure
2. Copies processed files to output location
3. Consolidates metadata
4. Generates processing summary
5. Performs cleanup operations

## Metadata Management

### Phase-Specific Metadata

Each phase maintains its own metadata store with:
- Processing status
- Phase version
- Changes made
- Error tracking
- Output file references

### Metadata Versioning

Phases track changes through versioned metadata:
```python
metadata.add_version(
    phase=self.name,
    changes=["Change description"],
)
```

### Error Handling

Phases implement consistent error handling:
```python
try:
    # Processing logic
except Exception as e:
    logger.error(f"Failed to process file {file_path}: {str(e)}")
    if metadata:
        metadata.add_error(self.__class__.__name__, str(e))
    return None
```

## Directory Structure

The phase system maintains a structured output directory:

```
_NovaProcessing/
├── phases/
│   ├── parse/
│   │   └── {filename}.parsed.md
│   ├── disassemble/
│   │   ├── {filename}.summary.md
│   │   └── {filename}.raw_notes.md
│   ├── split/
│   │   ├── {filename}.summary.md
│   │   ├── {filename}.details.md
│   │   ├── {filename}.notes.md
│   │   └── {filename}.references.md
│   └── finalize/
│       └── {filename}/
│           ├── summary.md
│           ├── details.md
│           ├── notes.md
│           └── references.md
└── metadata/
    └── {phase}/
        └── {filename}.metadata.json
```

## Best Practices

### Phase Development
1. Inherit from `Phase` base class
2. Implement required methods
3. Handle all error cases
4. Validate metadata
5. Follow output conventions

### Error Management
1. Use try-except blocks
2. Log detailed errors
3. Update metadata
4. Maintain processing state
5. Provide fallback behavior

### Metadata Handling
1. Create metadata if not provided
2. Update base metadata fields
3. Track phase-specific changes
4. Store metadata after processing
5. Handle metadata versioning

### Output Management
1. Create necessary directories
2. Use consistent naming conventions
3. Handle file permissions
4. Clean up temporary files
5. Validate output structure
``` 