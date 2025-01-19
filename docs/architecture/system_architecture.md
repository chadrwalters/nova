# Nova System Architecture

## 1. Overview

Nova is a Python-based system for processing, storing, and searching notes and documents using vector embeddings. It provides a robust API for integrating with various tools and services.

### Key Components

1. Vector Store:
   - ChromaDB-based storage
   - Semantic search capabilities
   - Document chunking and embedding
   - Metadata management

2. Processing Pipeline:
   - Multi-format document support
   - Intelligent chunking
   - Metadata extraction
   - Tag processing

3. MCP Server:
   - FastAPI-based implementation
   - RESTful API endpoints
   - Async operation support
   - Structured error handling

4. Monitoring System:
   - Health checks
   - Performance metrics
   - Resource monitoring
   - Log management

### System Requirements

- Python 3.11+
- ChromaDB
- Sentence Transformers
- FastAPI
- Rich (for logging)

## 2. Core Components

### Vector Store

#### Storage Layer
- ChromaDB backend
- Persistent storage in .nova/vectors
- Memory-efficient operation
- Automatic cleanup

#### Search Engine
- Semantic similarity search
- Tag-based filtering
- Relevance scoring
- Result ranking

#### Document Management
- Chunk storage
- Metadata indexing
- Version tracking
- Cache management

### Processing Pipeline

#### Document Handlers
- Markdown processor
- PDF processor
- Office formats
- Plain text

#### Chunking System
- Smart text splitting
- Heading preservation
- Context maintenance
- Metadata extraction

#### Tag System
- Automatic tagging
- Tag inheritance
- Tag normalization
- Tag search

## 3. API Layer

### MCP Server

#### Core Features
- RESTful endpoints
- Async operations
- JSON responses
- Error handling

#### Endpoints
- /search
- /health
- /monitor
- /process

#### Security
- Input validation
- Rate limiting
- Error boundaries
- Safe defaults

### Client Integration

#### API Clients
- Python SDK
- CLI tools
- HTTP clients
- WebSocket support

#### Response Format
- JSON structure
- Status codes
- Error messages
- Metadata

## 4. System Health

### Components
- Memory Monitor:
  - Usage tracking and trends
  - Peak detection
  - Warning thresholds
- Disk Monitor:
  - Space utilization
  - Directory health
- Vector Store Monitor:
  - Document statistics
  - Chunk distribution
  - Performance metrics
- Process Monitor:
  - CPU usage
  - Response times
  - Error rates

### Statistics Collection
- Document metrics
- Processing performance
- Search efficiency
- Resource utilization

## 5. Testing Infrastructure

### Test Architecture
- Pytest-based test suite
- Async test support with pytest-asyncio
- FastAPI TestClient integration
- Temporary directory fixtures
- Vector store test fixtures

### Test Coverage
- Tool Function Tests:
  - Input validation
  - Error handling
  - Response formats
  - Edge cases
- Integration Tests:
  - Server initialization
  - Tool registration
  - Vector store operations
  - File system operations
- Health Check Tests:
  - Component status
  - Metric collection
  - Log management

### Test Fixtures
- Vector Store:
  - Temporary database
  - Test collections
  - Cleanup handling
- File System:
  - Temporary directories
  - Test files
  - Cleanup management
- Server:
  - Test client
  - Tool registration
  - Response validation

## Package Management

### Dependencies
- Core requirements in pyproject.toml
- Development dependencies
- Optional features
- Version constraints

### Installation
- uv-based installation
- Development setup
- Test environment
- Documentation build
