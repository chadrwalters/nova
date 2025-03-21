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
  - Image Formats:
    + PNG:
      - Metadata extraction requirements:
        * Basic attributes (dimensions, color mode)
        * Format-specific metadata (gamma, sRGB)
        * Error handling for corrupt files
    + GIF:
      - Animation support requirements:
        * Frame count tracking
        * Duration information
        * Loop count handling
        * Animation state detection
    + WebP:
      - Format requirements:
        * Lossless/lossy detection
        * Quality metrics
        * Animation support
        * ICC profile handling
        * EXIF/XMP support
    + SVG:
      - Processing requirements:
        * XML structure validation
        * Element counting and analysis
        * Viewbox/dimension extraction
        * Title/description parsing
        * Namespace handling
    + Common Requirements:
      - EXIF metadata handling:
        * Camera information (make, model)
        * Date/time extraction
        * GPS data support
        * Copyright information
      - Error handling:
        * Format validation
        * Corrupt file detection
        * Recovery strategies
      - Output requirements:
        * Markdown conversion
        * Rich metadata preservation
        * Structured error reporting

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
- ChromaDB vector store:
  - Persistent storage in .nova/vectors
  - Collection-based organization
  - Cosine similarity search
  - Metadata filtering
  - Statistics persistence
  - Health monitoring
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

### 4.4 Server Architecture

#### Server Types

1. Nova MCP Server (`nova.cli.commands.nova_mcp_server`):
   - Core functionality
   - Vector search capabilities
   - System monitoring
   - Health checks
   - Port 8765 (default)

2. Echo Server (`nova.examples.mcp.echo_server`):
   - Example implementation
   - Basic tool registration
   - Error handling demonstration
   - Port 8766 (default)

#### Core Tools
- search_tool:
  - Semantic search
  - Configurable limits
  - Similarity scoring
  - Metadata filtering
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

### 4.5 Monitoring System [IMPLEMENTED]

#### Health Monitoring Requirements
- Real-time system health tracking:
  - Memory usage monitoring
    - Current usage tracking
    - Peak usage detection
    - Warning thresholds
  - CPU utilization tracking
    - Usage percentage
    - Load monitoring
    - Performance metrics
  - Disk space monitoring
    - Space utilization
    - Free space tracking
    - Directory health
  - Directory health checks
    - Path validation
    - Permission checks
    - Structure verification

#### Warning System Requirements
- Comprehensive warning management:
  - Warning categories
    - Memory warnings
    - Disk warnings
    - CPU warnings
    - Directory warnings
    - Vector store warnings
    - Metadata warnings
  - Severity levels
    - Info level for notifications
    - Warning level for attention
    - Critical level for urgent issues
  - Warning features
    - Warning persistence
    - History tracking
    - Resolution tracking
    - Category filtering
    - Severity filtering

#### Statistics Requirements
- Vector store statistics:
  - Document statistics
    - Total document count
    - Document types breakdown
    - Size distribution analysis
  - Chunk statistics
    - Total chunk count
    - Average per document
    - Size distribution
  - Tag statistics
    - Total tag count
    - Unique tag analysis
    - Tag relationships
  - Performance metrics
    - Search performance
    - Error rates
    - Response times

#### Output Format Requirements
- Text output format:
  - Rich console integration
    - Color-coded status
    - Progress indicators
    - Formatted tables
  - Style configuration
    - Color schemes
    - Status indicators
    - Text styling
- JSON output format:
  - Machine-readable structure
    - Nested data format
    - Type safety
    - Schema validation
  - Format features
    - Pretty printing
    - Syntax highlighting
    - Error handling

#### Command Interface Requirements
- Monitor command structure:
  - health subcommand
    - Watch mode support
    - Color output control
    - Format selection
    - Verbose mode for statistics
    - Health status display
    - Performance metrics
    - Document statistics
    - Chunk statistics
    - Tag statistics
  - warnings subcommand
    - Category filtering
    - Severity filtering
    - History viewing
    - Limit control

#### Integration Requirements
- System integration:
  - Automatic metrics recording
  - Resource cleanup
  - State persistence
  - Cross-session tracking
- Error management:
  - Structured error tracking
  - Pattern analysis
  - Recovery procedures
  - Prevention strategies

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
