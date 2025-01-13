# Nova V1: Product Requirements Document (PRD)

## 1. Introduction

### Product Name
Nova

### Purpose
- Ingest and unify Bear.app notes using docling's document processing pipeline
- Provide a semantic chunking and embedding layer for retrieving relevant data
- Use Anthropic's Claude with the official Model-Context Protocol (MCP) SDK for structured RAG queries
- Offer a minimal web interface to monitor or inspect system status (performance, logs, chunk stats)

### Scope
1. Local or optional cloud deployment
2. Ephemeral data handling and minimal logging
3. uv-based environment and dependency management

## 2. Objectives

1. **Consistent Data Consolidation**
   - Pull all Bear.app notes + attachments into a single repository
   - Reference attachments inline or place them near parent notes

2. **MCP-Driven Claude Queries**
   - Leverage official MCP SDK for structured data handling
   - Manage ephemeral data, system instructions, and user content

3. **Simple Monitoring Web App**
   - Show system metrics (chunk counts, conversion logs, recent requests)
   - Provide read-only interface

4. **Security & Ephemeral Data**
   - Enforce ephemeral boundaries in memory or short-lived caches
   - Ensure no long-term retention of ephemeral content

## 3. User Stories

1. As a user, I export my Bear.app notes, run Nova's ingestion pipeline, and query my notes via Claude while Nova retrieves relevant information through an MCP-compliant RAG pipeline.

2. As a user, I open a local web dashboard to check processed attachments, OCR errors, and vector store chunk counts.

3. As a user, I trust that ephemeral data won't leak or remain stored in logs or monitoring UI.

## 4. Functional Requirements

### 4.1 Bear Export & File Conversion [REFACTORING]
- Docling-based document processing:
  + Native format detection and conversion
  + Built-in text extraction and OCR
  + Rich metadata preservation
  + Attachment handling with versioning
  + Integrated error handling and logging

### 4.2 Vector Store Layer [IMPLEMENTED]
- Hybrid chunking combining:
  - Heading-based segmentation with hierarchy preservation
  - Semantic content splitting with word boundary detection
  - Configurable chunk sizes (min=100, max=512, overlap=50)
- Sentence transformer embeddings:
  - all-MiniLM-L6-v2 model
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

### 4.3 CLI Interface [IN PROGRESS]
- Command-line interface architecture:
  - Unified command structure with base command class
  - Plugin-based extensibility with automatic discovery
  - Rich terminal output and error handling
  - Standardized logging and progress tracking
- Core commands:
  - nova process-notes:
    - Process Bear exports with configurable paths
    - Handle OCR conversion and metadata
    - Track progress with rich output
    - Validate input and output directories
  - nova process-vectors:
    - Vector store operations with batch support
    - Cache management and persistence
    - Configurable chunking parameters
    - Progress tracking for long operations
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

### 4.4 MCP Integration with Claude [PLANNED]
- Official MCP SDK integration:
  - Dedicated mcp module
  - Data retrieval interface
  - MCP adapter implementation
- Tool definitions:
  - search_documentation
  - list_sources
  - extract_content
  - remove_documentation
- Context block handling:
  - Ephemeral data in memory
  - Resource block persistence
  - System instruction management

### 4.5 Monitoring System [PLANNED]
- FastAPI-based web server:
  - Health check endpoint
  - Basic metrics display
  - Recent ingestion stats
- Structured logging:
  - structlog integration
  - Consistent log format
  - Log rotation
- Performance metrics:
  - Vector store statistics
  - Query performance
  - System health
- API endpoints:
  - /health for system status
  - /metrics for performance data
  - /stats for processing statistics

## 5. Non-Functional Requirements

1. **Performance**
   - Few seconds response time for typical queries
   - Stable performance with thousands of notes
   - Efficient resource utilization:
     - Memory management
     - CPU optimization
     - Disk space monitoring

2. **Scalability**
   - Handle large note collections efficiently
   - Maintain performance with growing data
   - Resource-aware processing:
     - Batch operations
     - Caching strategies
     - Async processing

3. **Reliability**
   - Graceful handling of conversion failures
   - Robust ephemeral data management
   - Error recovery:
     - Automatic retries
     - Failure logging
     - Status tracking

4. **Security**
   - No sensitive data exposure
   - Proper ephemeral data handling
   - API key management:
     - Secure storage
     - Access control
     - Key rotation

5. **Development**
   - uv-based environment management:
     - Dependency locking
     - Virtual environment isolation
     - Package versioning
   - Testing infrastructure:
     - Unit test coverage
     - Integration testing
     - End-to-end validation
   - Documentation:
     - Setup guides
     - API reference
     - Usage examples

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
