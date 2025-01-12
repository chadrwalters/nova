# Nova System Architecture

## Core Architecture Principles

1. **Local-First Design**
   - Primary deployment on user's machine
   - Optional cloud deployment with enhanced security
   - Ephemeral data handling in memory
   - uv-based package management
   - Centralized .nova directory for system files
   - Configurable input directory

2. **Modular Components**
   - Independent service layers
   - Clear interfaces between components
   - Pluggable implementations (e.g., vector stores)

## System Components

### 1. Data Ingestion Layer

#### Bear Export Handler [IMPLEMENTED]
- Processes Bear.app exports (Markdown + attachments)
- Maintains link integrity and metadata
- Handles file organization and structure
- Tag Processing:
  - Code block-aware extraction
  - Metadata validation
  - Punctuation handling
  - Nested tag support (#tag/subtag)
  - Tag inheritance from metadata
- Error Handling:
  - Hierarchical error system (BearParserError, AttachmentError, OCRError)
  - Specific error types with context
  - Graceful degradation with logging
- Attachment Management:
  - Image detection (.png, .jpg, .jpeg, .gif, .bmp)
  - Metadata handling with versioning
  - OCR integration with EasyOCR
- Current Status:
  - Core parsing functionality verified
  - Metadata generation working
  - Tag extraction operational
  - OCR pipeline ready
  - Test suite passing
  - Python environment configured
  - Dependencies resolved
  - Placeholder system operational

#### OCR Integration [IMPLEMENTED]
- EasyOCR-based text extraction:
  - Confidence scoring with 50% threshold
  - Multiple OCR configurations for quality/speed tradeoff
  - Async processing with fallback mechanisms
  - Python 3.10 environment required
  - Proper import path: nova.bear_parser.ocr
- Error Handling:
  - Structured OCR errors with detailed messages
  - Placeholder generation for failed OCR:
    - JSON format with version tracking
    - Original file reference
    - Error details and timestamps
    - Automatic cleanup after 30 days
  - Configurable output to .nova directory:
    - Placeholders in .nova/placeholders/ocr
    - Processing files in .nova/processing/ocr
    - Logs in .nova/logs
- Current Status:
  - Core OCR functionality verified
  - Test suite passing
  - Python environment configured
  - Dependencies resolved
  - Placeholder system operational

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
  - all-MiniLM-L6-v2 model support
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
- Standalone processing:
  - Direct text to vector pipeline
  - Heading-aware chunking
  - Cached embeddings
  - Structured output format:
    - chunk_N.txt: Text chunks with context
    - embedding_N.npy: NumPy array embeddings
- Bear note integration:
  - Metadata preservation
  - Tag-aware processing
  - Source attribution
  - Per-note organization:
    - note_title/chunk_N.txt
    - note_title/embedding_N.npy
- Directory structure:
  - .nova/vector_store/embeddings
  - .nova/vector_store/cache
  - .nova/vector_store/index
- Current Status:
  - Core functionality verified
  - Test suite passing
  - Bear note integration complete
  - Processing scripts operational
  - CLI modules implemented:
    - process_vectors: Standalone text processing
    - process_bear_vectors: Bear note integration

### 3. RAG Orchestration Layer

#### CLI Architecture [COMPLETED]
- Command Structure:
  - src/nova/cli/
    - main.py: Command dispatcher with dynamic command discovery
    - commands/: Individual command modules with base command class
    - utils/: Shared CLI utilities and error handling
- Core Commands:
  - process-notes:
    - Bear note processing with configurable paths
    - OCR handling and metadata generation
    - Progress tracking with rich output
    - Async note processing with error recovery
    - Configurable input/output paths
  - process-vectors:
    - Vector store operations with batch support
    - Cache management and persistence
    - Configurable chunking parameters
    - Numpy-based embedding storage
    - Structured output format
  - monitor:
    - Health checks and system status
    - Statistics and metrics display
    - Log viewing and filtering
    - Rich table-based output
    - Real-time system monitoring
- Command Registration:
  - Plugin-based architecture with base command class
  - Automatic command discovery and registration
  - Standardized error handling and logging
  - Type-safe command interfaces
  - Click-based command creation
- Console Integration:
  - pyproject.toml entrypoints for nova command
  - Shell completion support
  - Unified error handling with click.Abort
  - Rich terminal output formatting
  - Color-coded status indicators
- Progress Feedback:
  - Rich progress bars for long operations
  - Structured status updates
  - Error reporting with context
  - Color-coded output formatting
  - Operation status tracking
- Error Handling:
  - Input validation with descriptive messages
  - Path existence verification
  - Operation status tracking
  - Recovery suggestions
  - Partial progress preservation
- Testing:
  - Comprehensive unit test suite
  - Integration tests for commands
  - Mock-based testing
  - Click test runner integration
  - Help text verification

#### MCP Integration [PLANNED]
- Dedicated MCP module (src/nova/mcp):
  - Data retrieval interface
  - MCP adapter implementation
  - API key configuration
- Tool Definitions:
  - search_documentation: Vector-based search through notes
  - list_sources: Display available note collections
  - extract_content: Process and analyze note content
  - remove_documentation: Delete specific notes/attachments
- Context Block Structure:
  - Ephemeral blocks for sensitive content
  - Resource blocks for persistent data
  - System instruction blocks for Claude guidance
- Transport Layer:
  - Local IPC communication
  - Async/await pattern for operations
  - Proper resource cleanup
- Error Handling:
  - Graceful degradation on failures
  - Clear error messages to Claude
  - Automatic retries for transient issues

### 4. Monitoring System [PLANNED]

#### Backend Services
- FastAPI-based server:
  - Health check endpoint
  - Basic metrics display
  - Recent ingestion stats
- Structured Logging:
  - structlog integration
  - Consistent log format
  - Log rotation and cleanup
- Metrics Collection:
  - Vector store statistics
  - Query performance tracking
  - System health monitoring
- API Endpoints:
  - /health: System status
  - /metrics: Performance data
  - /stats: Processing statistics

#### Performance Monitoring
- Resource Usage:
  - Memory consumption
  - CPU utilization
  - Disk space tracking
- Operation Metrics:
  - Ingestion throughput
  - Query latency
  - Vector store performance
- Error Tracking:
  - Failure rates
  - Error patterns
  - Recovery success

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant BearHandler
    participant Docling
    participant VectorStore
    participant MCP
    participant Claude
    participant Monitor

    User->>CLI: Command
    CLI->>BearHandler: Process Notes
    BearHandler->>Docling: Convert Attachments
    Docling-->>BearHandler: Converted Content
    BearHandler->>VectorStore: Store Chunks
    User->>CLI: Query
    CLI->>MCP: Process Query
    MCP->>VectorStore: Retrieve Context
    VectorStore-->>MCP: Relevant Chunks
    MCP->>Claude: Request
    Claude-->>MCP: Response
    MCP-->>User: Answer
    Monitor->>VectorStore: Collect Metrics
    Monitor->>MCP: Track Performance
```

## Development Architecture

### Environment Management
- uv-based dependency management:
  - pyproject.toml for package metadata
  - uv.lock for dependency locking
  - Virtual environment isolation
- Setup Process:
  1. Install uv: `brew install uv` or `pip install uv`
  2. Initialize environment: `uv venv`
  3. Install dependencies: `uv sync`
  4. Activate environment: `source .venv/bin/activate`

### Testing Strategy
- Test Organization:
  - tests/unit/: Unit tests by module
  - tests/integration/: Cross-module tests
  - tests/e2e/: End-to-end workflows
- Test Runner:
  - pytest with verbose output
  - Type checking with mypy
  - Command: `uv run mypy src tests && uv run pytest -v`

### Documentation Structure
- README.md:
  - Quick start guide
  - Environment setup
  - Command reference
- docs/architecture/: Technical design
- docs/prd/: Product requirements
- Developer guide:
  - Setup instructions
  - Testing procedures
  - Contribution guidelines

## Security Architecture

### Local Deployment
- Minimal authentication required
- File system security
- Memory-only ephemeral data
- Secure API key handling

### Cloud Deployment (Optional)
- Token-based authentication
- TLS encryption
- Secure ephemeral data handling
- Access control

## Performance Architecture

### Optimization Strategies
1. Efficient chunking algorithms
2. Batch processing for embeddings
3. Vector store indexing optimization
4. Response streaming
5. Caching layers

### Resource Management
1. Memory-efficient data structures
2. Garbage collection optimization
3. Connection pooling
4. Batch operations

## Error Handling Architecture

### Failure Modes
1. Conversion failures
   - OCR processing errors
   - Image quality issues
   - Unsupported file formats
2. OCR errors
   - Low confidence scores
   - Failed text extraction
   - Image preprocessing failures
3. API rate limits
4. Network issues
5. Storage errors

### Recovery Strategies
1. Fallback mechanisms
   - Alternative OCR approaches
   - Placeholder content generation
   - Metadata preservation
2. Retry policies
3. Circuit breakers
4. Error logging
5. User notifications

## Testing Architecture

### Test Layers
1. Unit tests per component
2. Integration tests between layers
3. End-to-end system tests

### Test Infrastructure
1. Local test runners
2. Test data management

### Not In Scope
The following testing aspects are explicitly NOT included in the current architecture:
1. CI/CD pipelines
2. Code coverage tracking
3. Performance profiling
4. Security audits
5. Automated benchmarking

Our testing focus is on maintaining functionality through regular local testing during development.

## Deployment Architecture

### Local Setup
1. uv environment management
2. Configuration management
   - Input directory configuration
   - API keys and credentials
   - Vector store settings
3. File System Structure
   - .nova directory for all system files
     - Logs directory
     - Processing files
     - Vector store data
     - System state
   - Configurable input directory
     - Default: ~/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput
     - Bear.app exports
     - Attachments
4. Local services

### Cloud Setup (Optional)
1. Container orchestration
2. Service scaling
3. Monitoring integration
4. Backup strategies

## Future Extensibility

### Integration Points
1. Alternative vector stores
2. Different LLM providers
3. Additional file formats
4. Enhanced monitoring

### Scalability Paths
1. Distributed processing
2. Enhanced caching
3. Load balancing
4. Horizontal scaling

## Command-Line Interface

The system provides a unified command-line interface through the `nova` command with the following subcommands:

### Bear Note Processing
- `nova generate-metadata`: Generates metadata.json for Bear notes
  - Creates structured metadata for all notes
  - Extracts creation/modification dates
  - Maps attachment references
  - Builds initial tag list

- `nova process-notes`: Processes Bear notes using the parser
  - Parses all notes in configured input directory
  - Extracts tags with nested support
  - Processes image attachments with OCR
  - Generates OCR failure placeholders
  - Creates structured output in .nova directory

### Vector Store Processing
- `nova process-vectors`: Standalone vector store processing
  - Input: Raw text and output directory
  - Performs heading-aware document chunking
  - Generates embeddings with caching
  - Saves chunks and embeddings to specified directory

- `nova process-bear-vectors`: Bear note vector store integration
  - Input: Bear notes directory and output directory
  - Combines Bear parsing with vector store processing
  - Preserves metadata through processing pipeline
  - Creates note-specific output directories
  - Maintains heading context in chunks

All commands support:
- Configurable input/output paths
- Logging with customizable levels
- Error recovery and reporting
- Progress tracking for long operations
