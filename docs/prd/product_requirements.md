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

#### Format Support Requirements
- Text Formats:
  - Markdown (.md):
    + Primary format with full feature support
    + Complete metadata preservation
    + Tag and link processing
    + Attachment handling
  - Plain Text (.txt):
    + Basic conversion support
    + File metadata extraction
    + Simple formatting preservation
  - HTML (.html, .htm):
    + Link preservation
    + Table structure maintenance
    + Image reference handling
  - reStructuredText (.rst):
    + Section hierarchy preservation
    + Directive support
    + Cross-reference handling
  - AsciiDoc (.adoc):
    + Block and inline formatting
    + Table preservation
    + Attribute handling
  - Org Mode (.org):
    + Heading hierarchy
    + TODO state support
    + Property handling
  - Wiki (.wiki):
    + Basic formatting
    + Link transformation
  - LaTeX (.tex):
    + Math expression support
    + Section preservation
    + Bibliography handling

- Office Formats:
  - Word (.docx):
    + Style preservation
    + Table support
    + Image handling
    + Header/footer support
  - Excel (.xlsx):
    + Table structure
    + Sheet handling
    + Formula references
  - PowerPoint (.pptx):
    + Slide structure
    + Image/shape support
    + Notes extraction

- Other Formats:
  - PDF (.pdf):
    + Layout preservation
    + Text extraction
    + Image references

#### Bear Note Processing Requirements
- Title Processing:
  + Date Extraction:
    - Support for YYYYMMDD format
    - Support for YYYY-MM-DD format
    - Component extraction (year, month, day)
    - Weekday calculation
  + Title Cleanup:
    - Date removal
    - Whitespace handling
    - Subtitle extraction

- Tag Processing:
  + Tag Formats:
    - Simple tags (#tag)
    - Nested tags (#parent/child)
    - Multi-level tags (#one/two/three)
  + Hierarchy:
    - Parent-child relationships
    - Complete path preservation
    - Tag inheritance rules
  + Special Tags:
    - Bear-specific tag handling
    - System tag processing
    - User tag preservation

- Metadata Requirements:
  + Automatic Extraction:
    - Creation date from title
    - Modified date from file
    - Tag hierarchy
    - Title components
    - Attachment references
  + Enhanced Metadata:
    - Date components for filtering
    - Tag relationships
    - Source tracking
    - Processing metadata

- Attachment Handling:
  + Reference Processing:
    - Path extraction
    - Type detection
    - Link preservation
  + Content Management:
    - Inline content handling
    - Reference validation
    - Path normalization

#### Processing Requirements
- Format Detection:
  + Primary Method:
    - MIME type detection
    - Content-based analysis
    - Format validation
  + Fallback Method:
    - Extension-based detection
    - Format mapping
    - Validation rules

- Error Handling:
  + Validation:
    - Format compatibility
    - Content structure
    - Character encoding
  + Recovery:
    - Fallback procedures
    - Partial recovery
    - Error documentation
  + Reporting:
    - Structured logging
    - Warning collection
    - Statistics gathering

- Progress Monitoring:
  + Status Updates:
    - Detection progress
    - Conversion status
    - Completion tracking
  + User Feedback:
    - Progress indicators
    - Error summaries
    - Success metrics
  + Logging:
    - Process documentation
    - Error recording
    - Performance tracking

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
- Server Implementations:
  1. Claude Desktop Server (`nova.cli.commands.nova_mcp_server`):
     - READ-ONLY FastAPI-based server
     - Direct Claude Desktop integration
     - Minimal tool set for safety
     - Port 8765 (chosen to avoid conflicts)
     - Strict access control

  2. Full MCP Server (`nova.server.mcp`):
     - Complete implementation
     - Internal tools and testing
     - All operations supported
     - Not for Claude Desktop
     - Advanced error handling

- Core Tools (Claude Desktop):
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

- Extended Tools (Full Server):
  - process_notes_tool: Document processing and ingestion
    - Multi-format support
    - Automatic format detection
    - Rich metadata extraction
    - Progress tracking
  - clean_processing_tool: Safe cleanup of processed files
    - Selective cleanup
    - Directory validation
    - Progress tracking
  - clean_vectors_tool: Vector store maintenance
    - Safe deletion operations
    - Collection management
    - Progress tracking

### 4.5 Monitoring System [IMPLEMENTED]

#### Session-based Monitoring
- Real-time Performance Tracking:
  - Query response time measurement
  - Memory usage monitoring (peak and current)
  - CPU utilization tracking
  - Active processing status updates
- Health Checks:
  - Component connectivity validation
  - Resource availability monitoring
  - System integrity verification
  - Real-time status reporting
- Error Management:
  - Real-time error detection and logging
  - Error context preservation
  - Recovery guidance
  - Session error statistics

#### Persistent Monitoring
- Metrics Storage:
  - SQLite-based persistence in .nova/metrics
  - Cross-session data retention
  - Performance trend tracking
  - Error pattern analysis
- Health Tracking:
  - Component status history
  - Resource utilization patterns
  - Storage space monitoring
  - System recommendations
- Performance Analysis:
  - Daily and hourly metrics
  - Query pattern analysis
  - Resource usage trends
  - Optimization insights

#### Log Management
- Automated Operations:
  - Size-based log rotation (10MB default)
  - Age-based archival (7 days default)
  - Compressed storage (.gz format)
  - Archive cleanup (50 files max)
- Analysis Capabilities:
  - Structured log parsing
  - Error pattern detection
  - Warning frequency analysis
  - Performance anomaly identification
- Storage Optimization:
  - Configurable retention settings
  - Space utilization monitoring
  - Archive management
  - Directory organization

#### Integration Features
- Claude Desktop Integration:
  - READ-ONLY monitoring tools
  - Health check endpoints
  - Performance metrics
  - Log analysis capabilities
- Cleanup Procedures:
  - Automatic session cleanup
  - Metric persistence
  - Log rotation
  - Resource release
- Error Handling:
  - Structured error tracking
  - Pattern analysis
  - Recovery procedures
  - Prevention strategies

#### Core Tools
- monitor_tool Commands:
  - health: System component status
  - stats: Performance metrics
  - logs: Log analysis and filtering
  - errors: Error tracking and analysis
- Features:
  - Real-time monitoring
  - Cross-session analysis
  - Trend visualization
  - Health recommendations

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
