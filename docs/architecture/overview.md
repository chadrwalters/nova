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
  - Configurable chunk sizes (default 300-500 tokens)
  - Heading weight boosting for improved retrieval
- **Embedding Service**
  - Local: Sentence Transformers (all-MiniLM-L6-v2)
  - Optional: Cloud-based embeddings
- **Vector Store**
  - Dual store architecture:
    - Persistent store (FAISS/Chroma) for permanent data
    - Ephemeral store (in-memory FAISS) for temporary data
  - TTL-based cleanup for ephemeral data
  - Automatic expiration handling

### 3. RAG Orchestrator
- **Query Processing**
  - Parallel vector similarity search across both stores
  - Smart result merging
  - Automatic expired data filtering
- **MCP Integration**
  - Structured context building
  - Role-based message construction
  - Ephemeral data flagging
- **Ephemeral Management**
  - TTL tracking for temporary data
  - Automatic cleanup of expired entries
  - Isolation from persistent storage

### 4. LLM Interface
- **Claude Integration**
  - Direct API communication
  - Response processing
  - Error handling

## Key Technologies

### Core Dependencies
- Python 3.10+
- Poetry for dependency management
- Docling ≥0.3.0
- MCP SDK (modelcontextprotocol)
- Sentence Transformers ≥2.2.2
- FAISS/Chroma
- Anthropic API Client

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
   - Hybrid chunking
   - Embedding generation
   - Vector store indexing

3. **Query Flow**
   - User query reception
   - Vector similarity search
   - MCP context construction
   - Claude API interaction
   - Response delivery

## Security & Privacy

### Local Deployment
- Minimal authentication
- In-memory ephemeral data
- Limited logging

### Cloud Deployment (Optional)
- Token-based authentication
- TLS encryption
- Secure ephemeral data handling

## Performance Considerations

- Sub-5 second query response time
- Efficient chunk retrieval
- Optimized embedding generation
- Memory-efficient ephemeral data handling 