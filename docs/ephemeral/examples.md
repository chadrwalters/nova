# Ephemeral Data Examples

## Basic Usage

### Simple Data Storage
```python
from nova.ephemeral import EphemeralManager

# Initialize manager
manager = EphemeralManager()

# Store simple text
data_id = manager.add_data(
    content="Remember this for 5 minutes",
    ttl=300
)

# Retrieve data
data = manager.get_data(data_id)
if data:
    print(data.content)
```

### Vector Search
```python
import numpy as np
from nova.processing import EmbeddingService

# Initialize components
embedder = EmbeddingService()
manager = EphemeralManager(embedding_dim=384)

# Add data with embeddings
texts = [
    "First example text",
    "Second example text",
    "Third example text"
]

# Generate embeddings
chunks = [Chunk(content=text) for text in texts]
embeddings = embedder.embed_chunks(chunks)

# Store with embeddings
for text, embedding in zip(texts, embeddings):
    manager.add_data(
        content=text,
        embedding=embedding,
        ttl=300
    )

# Search
query = "example text"
query_embedding = embedder.embed_chunks([Chunk(content=query)])[0]
results = manager.search(query_embedding, k=2)
```

## Advanced Usage

### Chat History Management
```python
class ChatManager:
    def __init__(self):
        self.manager = EphemeralManager(
            default_ttl=3600,  # 1 hour default
            cleanup_interval=300  # Clean every 5 minutes
        )
        self.embedder = EmbeddingService()
    
    async def add_message(self, message: str, user_id: str):
        # Generate embedding
        embedding = await self.embedder.embed_chunks([
            Chunk(content=message)
        ])
        
        # Store message
        return self.manager.add_data(
            content=message,
            metadata={
                "user_id": user_id,
                "timestamp": time.time()
            },
            embedding=embedding[0]
        )
    
    async def get_similar_messages(self, query: str, k: int = 5):
        # Find similar messages
        query_embedding = await self.embedder.embed_chunks([
            Chunk(content=query)
        ])
        return self.manager.search(query_embedding[0], k=k)
    
    def extend_message_ttl(self, message_id: str):
        # Keep message for another hour
        return self.manager.extend_ttl(message_id, 3600)
```

### Session Management
```python
class SessionManager:
    def __init__(self):
        self.manager = EphemeralManager(
            default_ttl=1800,  # 30 minutes
            cleanup_interval=60
        )
    
    def create_session(self, user_id: str, data: dict):
        return self.manager.add_data(
            content=json.dumps(data),
            metadata={
                "user_id": user_id,
                "created_at": time.time()
            }
        )
    
    def get_session(self, session_id: str) -> Optional[dict]:
        data = self.manager.get_data(session_id)
        if data:
            return {
                "data": json.loads(data.content),
                "metadata": data.metadata,
                "expires_in": data.expiration - time.time()
            }
        return None
    
    def refresh_session(self, session_id: str) -> bool:
        return self.manager.extend_ttl(session_id, 1800)
```

### Search Results Caching
```python
class SearchCache:
    def __init__(self):
        self.manager = EphemeralManager(
            default_ttl=300,  # 5 minutes
            cleanup_interval=60,
            n_lists=100,  # Use IVF for better performance
            n_probe=25
        )
        self.embedder = EmbeddingService()
    
    async def cache_results(
        self,
        query: str,
        results: List[dict]
    ):
        # Generate embeddings for results
        texts = [r["content"] for r in results]
        chunks = [Chunk(content=text) for text in texts]
        embeddings = await self.embedder.embed_chunks(chunks)
        
        # Cache each result
        cached_ids = []
        for result, embedding in zip(results, embeddings):
            result_id = self.manager.add_data(
                content=result["content"],
                metadata={
                    "query": query,
                    "score": result["score"],
                    "timestamp": time.time()
                },
                embedding=embedding
            )
            cached_ids.append(result_id)
        
        return cached_ids
    
    async def find_similar(
        self,
        query: str,
        threshold: float = 0.8,
        k: int = 10
    ):
        # Search cache for similar results
        query_embedding = await self.embedder.embed_chunks([
            Chunk(content=query)
        ])
        
        results = self.manager.search(query_embedding[0], k=k)
        
        # Filter by similarity threshold
        return [
            {
                "content": r.chunk.content,
                "metadata": r.metadata,
                "score": r.score
            }
            for r in results
            if r.score >= threshold
        ]
```

## Error Handling Examples

### Graceful Degradation
```python
class RobustEphemeralStore:
    def __init__(self):
        try:
            self.manager = EphemeralManager(use_gpu=True)
        except Exception as e:
            logger.warning(f"Failed to initialize GPU store: {e}")
            self.manager = EphemeralManager(use_gpu=False)
    
    def safe_add(self, content: str, **kwargs) -> Optional[str]:
        try:
            return self.manager.add_data(content, **kwargs)
        except Exception as e:
            logger.error(f"Failed to add data: {e}")
            return None
    
    def safe_get(self, data_id: str) -> Optional[dict]:
        try:
            data = self.manager.get_data(data_id)
            if data:
                return {
                    "content": data.content,
                    "metadata": data.metadata
                }
        except Exception as e:
            logger.error(f"Failed to get data: {e}")
        return None
    
    def safe_search(
        self,
        query_vector: np.ndarray,
        k: int = 5
    ) -> List[dict]:
        try:
            results = self.manager.search(query_vector, k=k)
            return [
                {
                    "content": r.chunk.content,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
```

### Memory Management
```python
class MemoryAwareManager:
    def __init__(self, max_vectors: int = 100000):
        self.max_vectors = max_vectors
        self.manager = EphemeralManager(
            cleanup_interval=30,  # More frequent cleanup
            alert_manager=AlertManager(),
            memory_monitor=MemoryMonitor()
        )
    
    def add_with_limit(self, content: str, **kwargs) -> Optional[str]:
        # Check current size
        current_size = self.manager._vectors_gauge._value.get()
        
        if current_size >= self.max_vectors:
            logger.warning("Vector store at capacity")
            return None
        
        # Adjust TTL based on store size
        if current_size > self.max_vectors * 0.8:
            # Use shorter TTL when near capacity
            kwargs["ttl"] = min(kwargs.get("ttl", 300), 300)
        
        return self.manager.add_data(content, **kwargs)
``` 