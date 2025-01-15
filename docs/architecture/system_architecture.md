# Nova System Architecture

## Core Architecture Principles

1. **Local-First Design**
   - Primary deployment on user's machine
   - Optional cloud deployment with enhanced security
   - Ephemeral data handling in memory
   - uv-based package management (pip/python usage FORBIDDEN)
   - Centralized .nova directory for system files
   - Configurable input directory

2. **Modular Components**
   - Independent service layers
   - Clear interfaces between components
   - Pluggable implementations (e.g., vector stores)

3. **Separation of Concerns**
   - Data ingestion (CLI only)
   - Vector store management (CLI only)
   - Search processing (semantic similarity)
   - Orchestration layer

4. **Data Flow Architecture**
   - Input Layer (CLI)
     - Note processing
     - Format conversion
     - Metadata extraction
   - Vector Store Layer
     - Vector embeddings (sentence-transformers)
     - Metadata storage
     - Search capabilities
   - Search Layer
     - Semantic similarity search
     - Result formatting
     - Health monitoring

5. **Access Patterns**
   - Vector Store Write Operations (CLI Only)
     - Processing notes
     - Creating embeddings
     - Cleaning/maintenance
     - System updates
   - Vector Store Read Operations
     - Semantic search
     - Content retrieval
     - Health checks
     - Statistics

## System Components

### 1. Data Ingestion Layer

#### Document Processing [IMPLEMENTED]
- Docling Integration:
  + Rich document model with metadata
  + Format detection and validation
  + Automatic format conversion
  + Native attachment handling
  + Error recovery and logging

+ Format Support:
  + Text Formats:
    + Markdown (.md) - Native format
    + Plain text (.txt) - Direct conversion
    + HTML (.html, .htm) - via html2text
    + reStructuredText (.rst) - via docutils
    + AsciiDoc (.adoc, .asciidoc) - via asciidoc
    + Org Mode (.org) - via pandoc
    + Wiki (.wiki) - via pandoc
    + LaTeX (.tex) - via pandoc
  + Office Formats:
    + Word (.docx) - via pandoc
    + Excel (.xlsx) - via pandoc
    + PowerPoint (.pptx) - via pandoc
  + Other Formats:
    + PDF (.pdf) - via pandoc
  + Format Detection:
    + MIME type detection
    + File extension fallback
    + Validation rules
    + Error handling

+ Metadata Model:
  + Document title and date
  + Source format tracking
  + Tag preservation
  + Custom metadata fields
  + Attachment references

+ Error Management:
  + Format validation errors
  + Conversion failures
  + MIME type validation
  + Structured error reporting
  + Recovery strategies

+ Progress Tracking:
  + Format detection progress
  + Conversion status updates
  + Rich terminal output
  + Error summaries
  + Completion reporting

### 2. Vector Store Layer [IMPLEMENTED]

#### Chunking Engine [IMPLEMENTED]
- Hybrid chunking strategy:
  - Heading-based segmentation with hierarchy preservation
  - Semantic content splitting with word boundary detection
  - Configurable chunk sizes (min, max, overlap)
- Metadata preservation:
  - Source location tracking
  - Tag inheritance
  - Heading context maintenance
- Content type handling:
  - Markdown-aware processing
  - Structured text support
- Current Status:
  - Core chunking functionality verified
  - Test suite passing
  - Python environment configured
  - Dependencies resolved

#### Embedding Service [IMPLEMENTED]
- Sentence transformer integration:
  - paraphrase-MiniLM-L3-v2 model
  - 384-dimensional embeddings
  - MPS acceleration on macOS
- Batch processing support:
  - Configurable batch sizes
  - Memory-efficient processing
- Embedding caching:
  - Local cache in .nova/vector_store/cache
  - Model-specific caching
  - Cache key generation
  - NumPy array storage format
- Current Status:
  - Core embedding functionality verified
  - Test suite passing
  - Caching system operational
  - Integration with chunking engine verified

#### Vector Store Integration [IMPLEMENTED]
- Chroma-based vector store:
  - Persistent storage in .nova/vectors
  - Metadata preservation with embeddings
  - Efficient vector operations
  - Collection-based organization
  - Automatic ID generation
- Bear note integration:
  - Full note content embeddings
  - Rich metadata storage:
    - Source file path
    - Note title and date
    - Tags
  - Batch processing support
- Directory structure:
  - .nova/vectors/: Chroma database files
  - .nova/processing/: Processed notes
  - .nova/logs/: System logs
- Current Status:
  - Core functionality verified
  - Test suite passing
  - Bear note integration complete
  - Processing scripts operational
  - CLI modules implemented:
    - process-bear-vectors: Bear note vector processing
    - clean-vectors: Vector store cleanup
    - search: Semantic search functionality

### 3. Search Orchestration Layer

#### CLI Architecture [COMPLETED]
- Command Structure:
  - src/nova/cli/
    - main.py: Command dispatcher with dynamic command discovery
    - commands/: Individual command modules with base command class
    - utils/: Shared CLI utilities and error handling
- Core Commands:
  - process-notes:
    - Format detection and validation
    - Automatic format conversion
    - Rich progress tracking
    - Error handling and recovery
    - Configurable paths:
      - Input directory
      - Output directory
      - Default paths from config
    - Format support:
      - Markdown (native)
      - Plain text (direct)
      - HTML (conversion)
      - RST (conversion)
    - Progress reporting:
      - Format detection status
      - Conversion progress
      - File processing status
      - Error summaries
  - process-bear-vectors:
    - Bear note vector processing
    - Chroma vector store integration
    - Metadata preservation
    - Batch processing support
    - Configurable input/output paths
  - search:
    - Semantic search through vector embeddings
    - Configurable result limits
    - Rich result formatting with metadata
    - Content preview generation
    - Similarity score calculation:
      - Cosine distance normalization
      - 0-100% score range
      - Semantic similarity ranking
      - Consistent score distribution
  - clean-processing:
    - Safe cleanup of processed notes
    - Force flag for deletion
    - Directory validation
    - Error handling and logging
  - clean-vectors:
    - Vector store cleanup
    - Safe deletion with --force flag
    - Directory cleanup
    - Error handling and logging
  - monitor:
    - Health checks and system status
    - Statistics and metrics display
    - Log viewing and filtering
    - Rich table-based output
    - Real-time system monitoring

### 4. Monitoring System [IMPLEMENTED]

#### Backend Services
- FastMCP Integration:
  - Asynchronous FastAPI-based server
  - Tool-based architecture for extensibility
  - Standardized error handling and response formats
  - Health monitoring and diagnostics
  - Port 8765 (chosen to avoid common service conflicts)
- Core Tools:
  - process_notes_tool: Document processing and ingestion
  - search_tool: Semantic search with vector embeddings
  - monitor_tool: System health and statistics
  - clean_processing_tool: Safe cleanup of processed files
  - clean_vectors_tool: Vector store maintenance
- Structured Logging:
  - structlog integration
  - Consistent log format
  - Log rotation and cleanup
- Metrics Collection:
  - Vector store statistics
  - Query performance tracking
  - System health monitoring
- API Endpoints:
  - /tools/process_notes: Document processing endpoint
  - /tools/search: Semantic search endpoint
  - /tools/monitor: Health monitoring endpoint
  - /tools/clean_processing: Processing cleanup endpoint
  - /tools/clean_vectors: Vector store cleanup endpoint

#### MCP Tools [IMPLEMENTED]

1. **process_notes_tool**
   - Purpose: Process and ingest documents into the vector store
   - Features:
     - Multi-format document support
     - Automatic format detection
     - Rich metadata extraction
     - Progress tracking
   - Error Handling:
     - Format validation errors
     - Conversion failures
     - Path validation

2. **search_tool**
   - Purpose: Semantic search through vector embeddings
   - Features:
     - Configurable result limits
     - Rich result formatting
     - Metadata inclusion
     - Similarity scoring
   - Error Handling:
     - Query validation
     - Vector store access errors
     - Result formatting issues

3. **monitor_tool**
   - Purpose: System health and statistics monitoring
   - Features:
     - Component health checks
     - Vector store statistics
     - Processing metrics
     - Log analysis
   - Error Handling:
     - Component failures
     - Metric collection errors
     - Log access issues

4. **clean_processing_tool**
   - Purpose: Safe cleanup of processed documents
   - Features:
     - Selective cleanup
     - Directory validation
     - Progress tracking
   - Error Handling:
     - Path validation
     - Permission issues
     - File access errors

5. **clean_vectors_tool**
   - Purpose: Vector store maintenance and cleanup
   - Features:
     - Safe deletion operations
     - Collection management
     - Progress tracking
   - Error Handling:
     - Vector store access errors
     - Collection validation
     - Cleanup failures

### 5. Testing Infrastructure [IMPLEMENTED]

#### Test Architecture
- Pytest-based test suite
- Async test support with pytest-asyncio
- FastAPI TestClient integration
- Temporary directory fixtures
- Vector store test fixtures

#### Test Coverage
- Tool Function Tests:
  - Input validation
  - Error handling
  - Response formats
  - Edge cases
- Integration Tests:
  - FastMCP initialization
  - Tool registration
  - Vector store operations
  - File system operations
- Health Check Tests:
  - Component status
  - Metric collection
  - Log management

#### Test Fixtures
- Vector Store:
  - Temporary database
  - Test collections
  - Cleanup handling
- File System:
  - Temporary directories
  - Test files
  - Cleanup management
- FastMCP:
  - Test client
  - Tool registration
  - Response validation

## Package Management

- Use uv ONLY for all Python operations
- Direct pip usage is FORBIDDEN
- Direct python/python3 usage is FORBIDDEN
- All Python commands must go through uv

## File System Organization

- All system files MUST be stored in .nova directory:
  - .nova/processing/: Processed notes
  - .nova/vectors/: Vector store database
  - .nova/logs/: System logs
- Input files location must be configurable
- Default input path: /Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput

## Testing Architecture

- All tests MUST run through uv: `uv run pytest -v`
- Type checking MUST be run before tests
- Tests should run without approval
- Test command: `uv run pytest -v`
- Test organization:
  - Unit tests for core components
  - Integration tests for service layers
  - End-to-end tests for CLI commands
