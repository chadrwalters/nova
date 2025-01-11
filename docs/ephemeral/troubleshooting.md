# Ephemeral Data Troubleshooting Guide

## Common Issues

### 1. Data Expiring Too Quickly

**Symptoms:**
- Data not available when expected
- Short-lived data
- Inconsistent retrieval

**Possible Causes:**
1. Default TTL too short
2. Clock synchronization issues
3. Cleanup interval too aggressive

**Solutions:**
```python
# 1. Increase default TTL
manager = EphemeralManager(
    default_ttl=600,  # 10 minutes instead of 5
    cleanup_interval=120  # Less frequent cleanup
)

# 2. Add buffer time
ttl = 300 + 30  # Add 30-second buffer

# 3. Monitor expiration
data = manager.get_data(data_id)
if data:
    remaining = data.expiration - time.time()
    if remaining < 60:  # Less than a minute
        manager.extend_ttl(data_id, 300)
```

### 2. Memory Usage Issues

**Symptoms:**
- High memory usage
- Slow cleanup operations
- OOM errors

**Possible Causes:**
1. Too many vectors
2. Large metadata
3. Inefficient index type

**Solutions:**
```python
# 1. Use IVF index for large datasets
manager = EphemeralManager(
    n_lists=100,
    n_probe=25
)

# 2. Monitor and limit size
current_size = manager._vectors_gauge._value.get()
if current_size > 100000:
    # Trigger cleanup or reject new data
    pass

# 3. Use memory monitor
manager = EphemeralManager(
    memory_monitor=MemoryMonitor(
        max_memory_mb=1024,
        alert_threshold=0.8
    )
)
```

### 3. Search Performance Issues

**Symptoms:**
- Slow search times
- High latency
- Timeouts

**Possible Causes:**
1. Inefficient index type
2. Too many vectors
3. GPU issues

**Solutions:**
```python
# 1. Use GPU acceleration
manager = EphemeralManager(
    use_gpu=True,
    n_lists=100  # IVF for better performance
)

# 2. Monitor search latency
with manager._search_latency.time():
    results = manager.search(query_vector)
    if results:
        logger.info(f"Found {len(results)} results")

# 3. Implement timeout
async def search_with_timeout(
    manager: EphemeralManager,
    vector: np.ndarray,
    timeout: float = 1.0
):
    try:
        async with asyncio.timeout(timeout):
            return manager.search(vector)
    except asyncio.TimeoutError:
        logger.error("Search timed out")
        return []
```

### 4. GPU-Related Issues

**Symptoms:**
- GPU initialization failures
- CUDA errors
- Unexpected CPU fallback

**Solutions:**
```python
# 1. Check GPU availability
if not faiss.get_num_gpus():
    logger.warning("No GPUs available")
    use_gpu = False

# 2. Implement fallback
try:
    manager = EphemeralManager(use_gpu=True)
except Exception as e:
    logger.warning(f"GPU failed: {e}")
    manager = EphemeralManager(use_gpu=False)

# 3. Monitor GPU memory
def check_gpu_memory():
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.used / info.total
    except Exception:
        return None
```

## Monitoring and Debugging

### 1. Logging Configuration
```python
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add file handler
file_handler = logging.FileHandler('ephemeral.log')
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
```

### 2. Metric Collection
```python
from prometheus_client import start_http_server

# Expose metrics
start_http_server(8000)

# Monitor specific metrics
def monitor_metrics(manager: EphemeralManager):
    while True:
        print(f"Vectors: {manager._vectors_gauge._value.get()}")
        print(f"Memory: {manager._memory_gauge._value.get()}")
        print(f"Size: {manager._size_gauge._value.get()}")
        time.sleep(60)
```

### 3. Health Checks
```python
async def health_check(manager: EphemeralManager) -> bool:
    try:
        # Test basic operations
        test_id = manager.add_data(
            "health check",
            ttl=60
        )
        if not test_id:
            return False
        
        # Test retrieval
        data = manager.get_data(test_id)
        if not data:
            return False
        
        # Test search
        dummy_vector = np.zeros(manager.embedding_dim)
        results = manager.search(dummy_vector, k=1)
        if results is None:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
```

## Performance Optimization

### 1. Batch Operations
```python
async def batch_add(
    manager: EphemeralManager,
    items: List[dict],
    batch_size: int = 100
):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        embeddings = []
        for item in batch:
            if item.get("embedding") is not None:
                embeddings.append(item["embedding"])
        
        if embeddings:
            embeddings = np.stack(embeddings)
            for item, embedding in zip(batch, embeddings):
                manager.add_data(
                    content=item["content"],
                    embedding=embedding,
                    ttl=item.get("ttl", 300)
                )
```

### 2. Index Optimization
```python
def optimize_index_params(num_vectors: int) -> dict:
    if num_vectors < 1000:
        return {
            "n_lists": None,  # Use flat index
            "n_probe": None
        }
    elif num_vectors < 10000:
        return {
            "n_lists": 50,
            "n_probe": 10
        }
    else:
        return {
            "n_lists": 100,
            "n_probe": 25
        }
```

### 3. Memory Optimization
```python
def estimate_memory_usage(
    num_vectors: int,
    embedding_dim: int,
    avg_content_size: int = 100
) -> int:
    # Vector memory
    vector_memory = num_vectors * embedding_dim * 4  # float32
    
    # Metadata memory (rough estimate)
    metadata_memory = num_vectors * (
        avg_content_size +  # content
        100 +  # metadata dict overhead
        24     # Python object overhead
    )
    
    # Index overhead (rough estimate)
    index_overhead = vector_memory * 0.2
    
    return vector_memory + metadata_memory + index_overhead
```

## Recovery Procedures

### 1. Data Recovery
```python
async def recover_data(
    manager: EphemeralManager,
    backup_file: str
):
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        for item in backup_data:
            if time.time() < item["expiration"]:
                manager.add_data(
                    content=item["content"],
                    metadata=item["metadata"],
                    ttl=item["expiration"] - time.time()
                )
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
```

### 2. Index Rebuild
```python
async def rebuild_index(manager: EphemeralManager):
    try:
        # Create new index
        new_index = faiss.IndexFlatL2(manager.embedding_dim)
        
        # Collect valid vectors
        valid_vectors = []
        valid_data = {}
        
        for data_id, data in manager.data.items():
            if data.embedding is not None:
                valid_vectors.append(data.embedding)
                valid_data[len(valid_vectors) - 1] = data
        
        if valid_vectors:
            vectors = np.stack(valid_vectors)
            new_index.add(vectors)
        
        # Replace old index
        manager.index = new_index
        manager.data = valid_data
        manager._update_metrics()
        
        return True
    except Exception as e:
        logger.error(f"Index rebuild failed: {e}")
        return False
``` 