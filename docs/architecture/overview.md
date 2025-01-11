# Nova Architecture Overview

## System Components

### 1. Data Ingestion Layer
- **Bear.app Export Handler**
  - Processes Markdown files and attachments from Bear exports
  - Maintains link integrity and metadata
- **Docling Converter**
  - Converts PDFs, DOCX, images to text/markdown
  - Implements fallback mechanisms for failed conversions
  - OCR capabilities for images and scanned documents

### 2. Data Processing Pipeline
- **Chunking Engine**
  - Hybrid chunking combining heading-based and semantic segmentation
  - Configurable chunk sizes (default 500 characters)
  - Heading weight boosting for improved retrieval
  - Type-safe implementation with proper annotations
- **Embedding Service**
  - Local: Sentence Transformers (all-MiniLM-L6-v2)
  - Optional: Cloud-based embeddings
  - Batch processing support
- **Vector Store**
  - Dual store architecture:
    - Persistent store (numpy-based) for permanent data
    - Ephemeral store for temporary data
  - L2 distance-based similarity search
  - TTL-based cleanup for ephemeral data
  - Type-safe implementation with proper annotations

### 3. RAG Orchestrator
- **Query Processing**
  - Asynchronous query handling
  - Parallel vector similarity search across both stores
  - Smart result merging
  - Automatic expired data filtering
- **MCP Integration**
  - Structured context building
  - Role-based message construction
  - Ephemeral data flagging
- **Async Support**
  - Async/await pattern for all operations
  - Streaming query support
  - Proper coroutine handling

### 4. LLM Interface
- **Claude Integration**
  - Asynchronous API communication
  - Streaming response support
  - Automatic retry on rate limits
  - Type-safe implementation

## Key Technologies

### Core Dependencies
- Python 3.10+
- Poetry for dependency management
- Docling ≥0.3.0
- MCP SDK (modelcontextprotocol)
- Sentence Transformers ≥2.2.2
- NumPy for vector operations
- Anthropic API Client (async)

### Optional Components
- FastAPI/Flask for API layer
- Cloud deployment tools
- Authentication modules

## Data Flow

1. **Input**
   - Bear.app exports (MD + attachments)
   - File conversion via Docling
   - Unified markdown corpus creation

2. **Processing**
   - Type-safe hybrid chunking
   - Batched embedding generation
   - Vector store indexing

3. **Query Flow**
   - Async user query reception
   - Parallel vector similarity search
   - MCP context construction
   - Async Claude API interaction
   - Streaming response delivery

## Security & Privacy

### Local Deployment
- Minimal authentication
- In-memory ephemeral data
- Limited logging
- Type-safe data handling

### Cloud Deployment (Optional)
- Token-based authentication
- TLS encryption
- Secure ephemeral data handling

## Performance Considerations

- Sub-5 second query response time
- Efficient chunk retrieval with L2 distance
- Batched embedding generation
- Memory-efficient ephemeral data handling
- Async operations for improved throughput 