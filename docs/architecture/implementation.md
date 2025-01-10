# Technical Implementation Details

## Component Specifications

### Data Ingestion

```python
# Core ingestion interfaces
class BearExportHandler:
    def process_export(self, export_path: Path) -> MarkdownCorpus:
        """Process Bear.app export directory"""

class DoclingConverter:
    def convert_file(self, file_path: Path) -> ConversionResult:
        """Convert single file using Docling"""
    
    def handle_conversion_failure(self, file_path: Path) -> PlaceholderResult:
        """Generate appropriate placeholder for failed conversions"""
```

### Data Processing

```python
class ChunkingEngine:
    def chunk_document(
        self, 
        document: Document,
        chunk_size: int = 500,
        heading_weight: float = 1.5
    ) -> list[Chunk]:
        """Hybrid document chunking"""

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model"""
    
    def embed_chunks(self, chunks: list[Chunk]) -> np.ndarray:
        """Generate embeddings for chunks"""

class VectorStore:
    def __init__(self, embedding_dim: int = 384):
        """Initialize persistent vector store"""
        self.index = self._create_index(embedding_dim)
    
    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray):
        """Index chunks and embeddings"""
        # Ensure no ephemeral chunks in persistent store
        if any(c.is_ephemeral for c in chunks):
            raise ValueError("Cannot store ephemeral chunks in persistent store")
        self._add_to_index(chunks, embeddings)

class EphemeralVectorStore(VectorStore):
    def __init__(self, embedding_dim: int = 384):
        """Initialize in-memory vector store"""
        super().__init__(embedding_dim)
        self.chunk_registry = {}  # track chunk expiration
        self._lock = threading.Lock()  # thread safety for registry
    
    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray):
        """Store chunks with expiration tracking"""
        if not all(c.is_ephemeral for c in chunks):
            raise ValueError("All chunks must be marked ephemeral")
        
        with self._lock:
            super().add_chunks(chunks, embeddings)
            for chunk in chunks:
                # Sanitize metadata before storage
                chunk.metadata = self._sanitize_metadata(chunk.metadata)
                self.chunk_registry[chunk.id] = chunk.expiration
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> list[Chunk]:
        """Search with automatic expiration filtering"""
        with self._lock:
            # Pre-filter expired chunks
            now = time.time()
            valid_chunks = {
                chunk_id: exp 
                for chunk_id, exp in self.chunk_registry.items() 
                if exp > now
            }
            
            if not valid_chunks:
                return []
            
            # Only search over valid chunks
            results = self._search_filtered(
                query_embedding,
                valid_chunk_ids=list(valid_chunks.keys()),
                k=k
            )
            
            # Double-check expiration during results processing
            return [
                chunk for chunk in results
                if chunk.id in valid_chunks and 
                valid_chunks[chunk.id] > time.time()
            ]
    
    def _sanitize_metadata(self, metadata: dict) -> dict:
        """Remove sensitive fields from metadata"""
        ALLOWED_KEYS = {'timestamp', 'source', 'type'}
        return {
            k: v for k, v in metadata.items() 
            if k in ALLOWED_KEYS
        }
    
    def delete_chunk(self, chunk_id: str):
        """Remove expired chunk with cleanup"""
        with self._lock:
            if chunk_id in self.chunk_registry:
                # Clean metadata before removal
                chunk = self._get_chunk(chunk_id)
                if chunk:
                    chunk.metadata.clear()
                    chunk.embedding = None
                
                # Remove from index and registry
                del self.chunk_registry[chunk_id]
                self._remove_from_index(chunk_id)
```

### RAG Orchestration

```python
class RAGOrchestrator:
    def __init__(
        self,
        persistent_store: VectorStore,
        ephemeral_store: EphemeralVectorStore,
        ephemeral_manager: EphemeralDataManager
    ):
        self.persistent_store = persistent_store
        self.ephemeral_store = ephemeral_store
        self.ephemeral_manager = ephemeral_manager
    
    def process_query(
        self, 
        query: str,
        top_k: int = 5
    ) -> MCPPayload:
        """Full query processing pipeline"""
        query_embedding = self.embedder.embed_text(query)
        
        # Search both stores (ephemeral store handles expiration internally)
        persistent_results = self.persistent_store.search(
            query_embedding, k=top_k
        )
        ephemeral_results = self.ephemeral_store.search(
            query_embedding, k=top_k
        )
        
        # No need to filter expired chunks here - handled by store
        
        # Merge results with metadata sanitization
        combined = self._merge_results(
            persistent_results, 
            ephemeral_results
        )
        
        # Build MCP payload with clean metadata
        return self.build_mcp_context(
            query=query,
            chunks=combined,
            sanitize_metadata=True
        )
    
    def _merge_results(
        self,
        persistent: list[Chunk],
        ephemeral: list[Chunk]
    ) -> list[Chunk]:
        """Smart merging of results from both stores"""
        # Ensure no metadata leaks during merge
        for chunk in ephemeral:
            chunk.metadata = self.ephemeral_store._sanitize_metadata(
                chunk.metadata
            )
        
        # Implement merging logic (e.g., by score, recency)
        return sorted(
            persistent + ephemeral,
            key=lambda x: x.score,
            reverse=True
        )
```

```python
class EphemeralDataManager:
    def __init__(self, ephemeral_store: EphemeralVectorStore):
        self.store = ephemeral_store
        self.cleanup_thread = self._start_cleanup_thread()
    
    def store_ephemeral(self, data: list[Chunk], ttl: int = 300):
        """Store ephemeral data with TTL"""
        now = time.time()
        for chunk in data:
            chunk.expiration = now + ttl
            chunk.is_ephemeral = True
        
        embeddings = self.embedder.embed_chunks(data)
        self.store.add_chunks(data, embeddings)
    
    def filter_valid(self, chunks: list[Chunk]) -> list[Chunk]:
        """Return only non-expired chunks"""
        valid = []
        now = time.time()
        for chunk in chunks:
            if getattr(chunk, 'expiration', 0) > now:
                valid.append(chunk)
            else:
                self.store.delete_chunk(chunk.id)
        return valid
    
    def _start_cleanup_thread(self):
        """Background thread for expired data cleanup"""
        def cleanup_loop():
            while True:
                self._cleanup_expired()
                time.sleep(60)  # Check every minute
        
        thread = threading.Thread(
            target=cleanup_loop,
            daemon=True
        )
        thread.start()
        return thread
    
    def _cleanup_expired(self):
        """Remove all expired chunks"""
        now = time.time()
        expired = [
            chunk_id 
            for chunk_id, expiration 
            in self.store.chunk_registry.items()
            if expiration <= now
        ]
        for chunk_id in expired:
            self.store.delete_chunk(chunk_id)
```

### LLM Integration

```python
class ClaudeClient:
    def __init__(self, api_key: str):
        """Initialize Claude client"""
    
    def complete(
        self,
        mcp_payload: MCPPayload,
        max_tokens: int = 1000
    ) -> str:
        """Send MCP payload to Claude and get response"""
```

## Key Interfaces

### Document Types

```python
@dataclass
class Document:
    content: str
    metadata: dict
    source_path: Path

@dataclass
class Chunk:
    content: str
    metadata: dict
    embedding: Optional[np.ndarray] = None
    is_ephemeral: bool = False
```

### MCP Types

```python
@dataclass
class MCPPayload:
    system_instructions: str
    developer_instructions: str
    user_message: str
    context_blocks: list[ContextBlock]

@dataclass
class ContextBlock:
    content: str
    metadata: dict
    ephemeral: bool = False
```

## Configuration

```yaml
# Default configuration (nova.yaml)
ingestion:
  chunk_size: 500
  heading_weight: 1.5
  
embedding:
  model: "all-MiniLM-L6-v2"
  dimension: 384
  
vector_store:
  engine: "faiss"  # or "chroma"
  
rag:
  top_k: 5
  
llm:
  model: "claude-2"
  max_tokens: 1000
  
security:
  ephemeral_ttl: 300  # seconds
```

## Error Handling

### Conversion Errors
- Generate placeholders for failed conversions
- Log error details without sensitive content
- Allow manual review of failed items

### Query Errors
- Implement retries for API failures
- Provide meaningful error messages
- Maintain data privacy in error logs

## Deployment

### Local Setup
```bash
# Install dependencies
poetry install

# Configure environment
export ANTHROPIC_API_KEY="your_key_here"

# Run locally
poetry run nova
```

### Cloud Setup (Optional)
```bash
# Additional cloud dependencies
poetry install --extras cloud

# Configure cloud environment
export NOVA_AUTH_TOKEN="your_token_here"
export NOVA_TLS_CERT="/path/to/cert"

# Run with cloud options
poetry run nova --cloud
``` 