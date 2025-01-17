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

+ Format Support and Processing:
  + Text Formats:
    + Markdown (.md):
      - Native format with full structure preservation
      - Direct metadata extraction
      - Tag and link processing
      - Attachment reference handling
    + Plain text (.txt):
      - Direct conversion with line breaks
      - Basic metadata from file system
      - Simple structure preservation
    + HTML (.html, .htm):
      - Converted via html2text
      - Link preservation with references
      - Table structure maintenance
      - Image reference extraction
    + reStructuredText (.rst):
      - Converted via docutils
      - Section hierarchy preservation
      - Directive handling
      - Cross-reference processing
    + AsciiDoc (.adoc, .asciidoc):
      - Converted via asciidoc
      - Block and inline formatting
      - Table and list preservation
      - Attribute handling
    + Org Mode (.org):
      - Converted via pandoc
      - Heading hierarchy preservation
      - TODO state handling
      - Tag and property processing
    + Wiki (.wiki):
      - Converted via pandoc
      - Wiki syntax conversion
      - Link transformation
      - Basic formatting
    + LaTeX (.tex):
      - Converted via pandoc
      - Math expression handling
      - Section structure preservation
      - Bibliography processing
  + Office Formats:
    + Word (.docx):
      - Converted via pandoc
      - Style preservation
      - Table and image handling
      - Header/footer processing
    + Excel (.xlsx):
      - Converted via pandoc
      - Table structure preservation
      - Sheet separation
      - Formula reference handling
    + PowerPoint (.pptx):
      - Converted via pandoc
      - Slide structure preservation
      - Image and shape handling
      - Notes extraction
  + Other Formats:
    + PDF (.pdf):
      - Converted via pandoc
      - Layout preservation attempt
      - Text extraction with positioning
      - Image reference handling

+ Bear Note Processing:
  + Title Processing:
    - Date Extraction:
      + Supported formats:
        - YYYYMMDD (e.g., 20240115)
        - YYYY-MM-DD (e.g., 2024-01-15)
      + Extracted components:
        - Year (numeric)
        - Month (numeric)
        - Day (numeric)
        - Weekday (string)
    - Title Cleanup:
      + Date removal
      + Whitespace normalization
      + Subtitle extraction
  + Tag Processing:
    - Extraction patterns:
      + Simple tags: #tag
      + Nested tags: #parent/child
      + Multi-level: #one/two/three
    - Hierarchy preservation:
      + Parent-child relationships
      + Tag inheritance in chunks
      + Complete path storage
    - Special handling:
      + Bear-specific tags
      + System tags
      + User-defined tags
  + Metadata Handling:
    - Automatic extraction:
      + Creation date from title
      + Modified date from file
      + Tag collection with hierarchy
      + Title and subtitle
      + Attachment references
    - Enhanced metadata:
      + Date components for filtering
      + Tag relationships
      + Source file tracking
      + Processing timestamp
  + Attachment Processing:
    - Reference extraction
    - Type detection
    - Path preservation
    - Inline content handling

+ Format Detection:
  + Primary: MIME type detection
    - python-magic library
    - Content-based detection
    - Reliable format identification
  + Fallback: Extension mapping
    - File extension analysis
    - Format validation
    - Conversion path selection
  + Validation rules:
    - Format compatibility check
    - Content structure validation
    - Character encoding verification

+ Error Management:
  + Format Validation:
    - MIME type mismatches
    - Unsupported formats
    - Encoding issues
  + Conversion Failures:
    - Tool errors
    - Content corruption
    - Resource limitations
  + Recovery Strategies:
    - Fallback conversions
    - Partial content recovery
    - Error documentation
  + Reporting:
    - Structured error logs
    - Warning collection
    - Processing statistics

+ Progress Tracking:
  + Status Updates:
    - Format detection progress
    - Conversion status
    - Processing completion
  + Rich Output:
    - Terminal progress bars
    - Error summaries
    - Success statistics
  + Logging:
    - Detailed process logs
    - Error documentation
    - Performance metrics

### 2. Vector Store Layer [IMPLEMENTED]

#### Vector Store Service [IMPLEMENTED]
- ChromaDB integration:
  - Persistent storage in .nova/vectors
  - Collection-based organization ("nova_notes")
  - Cosine similarity search
  - Metadata filtering support
- Statistics tracking:
  - Persistent stats in .nova/vectors/stats.json
  - Document counts and embeddings
  - Search metrics and cache hits
  - Last update timestamps
- Error handling:
  - Graceful collection management
  - Automatic recovery from corruption
  - Detailed error logging
- Health monitoring:
  - Collection existence verification
  - Database file checks
  - Statistics validation

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

#### Session Monitoring
- Real-time Performance Tracking:
  - Query response times
  - Memory usage monitoring
  - CPU utilization tracking
  - Active processing status
- Health Checks:
  - Vector store connectivity
  - Processing pipeline status
  - Resource availability checks
  - Component health validation
- Error Tracking:
  - Real-time error detection
  - Error context capture
  - Recovery suggestions
  - Session-based error counts

#### Persistent Monitoring
- Cross-session Metrics:
  - SQLite-based metrics storage in .nova/metrics
  - Session duration tracking
  - Query patterns and performance
  - Error frequency analysis
- System Health:
  - Vector store integrity checks
  - Input directory monitoring
  - Storage space tracking
  - Component status history
- Performance Analysis:
  - Daily and hourly statistics
  - Performance trend analysis
  - Resource utilization patterns
  - Query optimization insights

#### Log Management
- Automated Log Handling:
  - Rotation based on size and age
  - Compression and archival
  - Cleanup of old archives
  - Structured log parsing
- Analysis Tools:
  - Error pattern detection
  - Warning frequency analysis
  - Component-wise logging
  - Performance anomaly detection
- Storage Management:
  - Configurable retention policies
  - Archive size management
  - Log file organization
  - Space utilization monitoring

#### Backend Services
- FastMCP Server Implementations:
  1. Claude Desktop Server (`nova.cli.commands.nova_mcp_server`):
     - READ-ONLY implementation for direct Claude Desktop integration
     - Minimal tool set (search and monitoring only)
     - Strict access control
     - Port 8765 (chosen to avoid common service conflicts)
     - Optimized logging configuration
     - Safe import structure
     - Automatic startup through Claude Desktop

  2. Full MCP Server (`nova.server.mcp`):
     - Complete implementation with all operations
     - Used by internal tools and testing
     - Not for direct Claude Desktop integration
     - Comprehensive tool set
     - Advanced error handling
     - Performance monitoring
     - Resource management

#### Core Tools
- monitor_tool:
  - Health Command:
    - Real-time component status
    - Resource availability
    - System integrity checks
  - Stats Command:
    - Session statistics
    - Performance metrics
    - Query patterns
  - Logs Command:
    - Log analysis and filtering
    - Error summaries
    - Warning detection
  - Errors Command:
    - Error trend analysis
    - Common error patterns
    - Recovery suggestions

#### Integration Points
- Session Cleanup:
  - Automatic metrics recording
  - Log rotation on exit
  - Resource cleanup
  - State persistence
- Health Reporting:
  - Real-time status updates
  - Cross-session trends
  - System recommendations
  - Performance insights
- Error Management:
  - Structured error tracking
  - Pattern analysis
  - Recovery procedures
  - Prevention strategies

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
