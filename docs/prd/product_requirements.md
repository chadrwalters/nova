# Nova V1: Product Requirements Document (PRD)

## 1. Introduction

### Product Name
Nova

### Purpose
- Ingest and unify Bear.app notes with rich metadata extraction
- Provide semantic chunking and embedding layer for retrieving relevant data
- Offer a minimal web interface to monitor or inspect system status (performance, logs, chunk stats)

### Scope
1. Local or optional cloud deployment
2. Ephemeral data handling and minimal logging
3. uv-based environment and dependency management

## 2. Objectives

1. **Consistent Data Consolidation**
   - Pull all Bear.app notes + attachments into a single repository
   - Reference attachments inline or place them near parent notes

2. **Vector-Based Search**
   - Use sentence-transformers for semantic embeddings
   - Efficient vector storage and retrieval with Chroma
   - Semantic similarity search capabilities

3. **Simple Monitoring Web App**
   - Show system metrics (chunk counts, conversion logs, recent requests)
   - Provide read-only interface

4. **Security & Ephemeral Data**
   - Enforce ephemeral boundaries in memory or short-lived caches
   - Ensure no long-term retention of ephemeral content

## 3. User Stories

1. As a user, I export my Bear.app notes, run Nova's ingestion pipeline, and search my notes using semantic similarity.

2. As a user, I open a local web dashboard to check processed attachments, OCR errors, and vector store chunk counts.

3. As a user, I trust that ephemeral data won't leak or remain stored in logs or monitoring UI.

## 4. Functional Requirements

### 4.1 Document Processing [IMPLEMENTED]
- Rich document processing:
  + Native format detection and conversion
  + Built-in format validation
  + Rich metadata preservation
  + Attachment handling with versioning
  + Integrated error handling and logging

- Format Support:
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
  + Conversion Features:
    + Automatic format detection
    + Lossless when possible
    + Fallback strategies
    + Error recovery
    + Progress tracking

- Metadata Model:
  + Document title and date
  + Source format tracking
  + Tag preservation
  + Custom metadata fields
  + Attachment references

- Error Management:
  + Format validation errors
  + Conversion failures
  + MIME type validation
  + Structured error reporting
  + Recovery strategies

- Progress Tracking:
  + Format detection progress
  + Conversion status updates
  + Rich terminal output
  + Error summaries
  + Completion reporting

### 4.2 Vector Store Layer [IMPLEMENTED]
- Hybrid chunking combining:
  - Heading-based segmentation with hierarchy preservation
  - Semantic content splitting with word boundary detection
  - Configurable chunk sizes (min=100, max=512, overlap=50)
- Sentence transformer embeddings:
  - paraphrase-MiniLM-L3-v2 model
  - 384-dimensional vectors
  - MPS acceleration on macOS
  - Batch processing (size=32)
- Local caching system:
  - Model-specific caching
  - Cache key generation
  - Storage in .nova/vector_store/cache
- Integration scripts:
  - Standalone vector processing
  - Bear note integration
  - Detailed logging and error handling

### 4.3 CLI Interface [IMPLEMENTED]
- Command-line interface architecture:
  - Unified command structure with base command class
  - Plugin-based extensibility with automatic discovery
  - Rich terminal output and error handling
  - Standardized logging and progress tracking
- Core commands:
  - nova process-notes:
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
  - nova process-vectors:
    - Vector store operations with batch support
    - Cache management and persistence
    - Configurable chunking parameters
    - Progress tracking for long operations
  - nova search:
    - Semantic search through vector embeddings
    - Configurable result limits
    - Rich result formatting with metadata
    - Content preview generation
    - Normalized similarity scoring:
      - Cosine distance-based calculation
      - 0-100% score normalization
      - Semantic similarity ranking
      - Consistent score distribution
  - nova clean-processing:
    - Safe cleanup of processed notes
    - Force flag for deletion
    - Directory validation
    - Error handling and logging
  - nova clean-vectors:
    - Vector store cleanup
    - Force flag for deletion
    - Directory validation
    - Error handling and logging
  - nova monitor:
    - Health checks and system status
    - Statistics and metrics display
    - Log viewing with filtering
    - Real-time updates
- User experience:
  - Command completion with help text
  - Rich progress indicators for long operations
  - Structured error reporting with context
  - Consistent output formatting
- Documentation:
  - Comprehensive command reference
  - Detailed usage examples
  - Error handling guidelines
  - Configuration and setup guide

### 4.4 MCP Integration [IMPLEMENTED]
- FastMCP Integration:
  - Asynchronous FastAPI-based server
  - Tool-based architecture for extensibility
  - Standardized error handling and response formats
  - Health monitoring and diagnostics
  - Port 8765 (chosen to avoid common service conflicts)
- Core Tools:
  - process_notes_tool: Document processing and ingestion
    - Multi-format support
    - Automatic format detection
    - Rich metadata extraction
    - Progress tracking
  - search_tool: Semantic search through vector embeddings
    - Configurable result limits
    - Rich result formatting
    - Metadata inclusion
    - Similarity scoring
  - monitor_tool: System health and statistics
    - Component health checks
    - Vector store statistics
    - Processing metrics
    - Log analysis
  - clean_processing_tool: Safe cleanup of processed files
    - Selective cleanup
    - Directory validation
    - Progress tracking
  - clean_vectors_tool: Vector store maintenance
    - Safe deletion operations
    - Collection management
    - Progress tracking
- Error Handling:
  - Standardized error responses
  - Validation middleware
  - Detailed error messages
  - Recovery strategies
- Testing & Validation:
  - Comprehensive test suite
  - Integration tests
  - Tool functionality testing
  - Error handling verification
- Access Control:
  - READ-ONLY access to vector store
  - No direct write operations
  - All modifications through CLI only
  - Data integrity preservation

### 4.5 Monitoring System [IMPLEMENTED]
- FastMCP-based monitoring:
  - Health check endpoints
  - Tool-based metrics collection
  - System status monitoring
  - Log management
- Structured logging:
  - structlog integration
  - Consistent log format
  - Log rotation and cleanup
  - Error tracking
- Performance metrics:
  - Vector store statistics
  - Query performance tracking
  - System health monitoring
  - Resource utilization
- API endpoints:
  - /tools/process_notes: Document processing
  - /tools/search: Semantic search
  - /tools/monitor: Health monitoring
  - /tools/clean_processing: Processing cleanup
  - /tools/clean_vectors: Vector store cleanup
- Testing Infrastructure:
  - Pytest-based test suite
  - Async test support
  - FastAPI TestClient integration
  - Temporary test fixtures

## 5. Non-Functional Requirements

### 5.1 Performance
- Few seconds response time for typical queries
- Stable performance with thousands of notes
- Efficient resource utilization:
  - Memory management
  - CPU optimization
  - Disk space monitoring

### 5.2 Scalability
- Handle large note collections efficiently
- Maintain performance with growing data
- Resource-aware processing:
  - Batch operations
  - Caching strategies
  - Async processing

### 5.3 Reliability
- Graceful handling of conversion failures
- Robust error recovery
- Data integrity preservation

### 5.4 Package Management
- Use uv ONLY for all Python operations
- Direct pip usage is FORBIDDEN
- Direct python/python3 usage is FORBIDDEN
- All Python commands must go through uv

### 5.5 File System Organization
- All system files MUST be stored in .nova directory
- All logs, processing files, and system writes go to .nova
- Input files location must be configurable
- Default input path: /Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput

### 5.6 Testing
- Use uv run pytest for ALL test runs
- Tests should run without approval
- Test command: uv run pytest -v
- Type checking MUST be run before tests

## 6. Assumptions

1. Bear.app exports follow consistent structure
2. Valid Anthropic API key availability
3. Official MCP SDK compatibility
4. Local deployment capability
5. uv package manager availability

## 7. Constraints

1. Local-first deployment focus
2. Optional cloud deployment with security measures
3. Strict ephemeral data handling
4. uv-only package management
5. Python 3.10+ requirement

## 8. Future Enhancements

1. Direct Bear database integration
2. Multi-LLM support
3. Advanced monitoring features
4. Multi-user capabilities
5. Cloud deployment options

## 9. Success Metrics

1. User satisfaction and trust
2. Sub-5-second query performance
3. Effective monitoring capabilities
4. Modular and maintainable code
5. Comprehensive test coverage

## 10. Development Guidelines

1. **Environment Setup**
   - Install uv package manager
   - Create virtual environment
   - Install dependencies
   - Configure development tools

2. **Testing Requirements**
   - Run mypy type checking
   - Execute pytest test suite
   - Maintain test coverage
   - Document test cases

3. **Code Quality**
   - Follow PEP 8 style guide
   - Use type hints
   - Document public APIs
   - Write clear commit messages

4. **Documentation**
   - Update README.md
   - Maintain architecture docs
   - Document API changes
   - Create usage examples
