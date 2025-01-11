# Ephemeral Data System

## Overview

The ephemeral data system provides temporary storage for data that should automatically expire after a set time. It combines vector search capabilities with time-based expiration, making it ideal for temporary context, chat history, or session-specific data.

## Key Features

- Automatic data expiration with configurable TTL
- Vector similarity search using FAISS
- GPU acceleration support
- Memory usage monitoring and alerts
- Optimized cleanup mechanism
- Metric tracking and performance monitoring

## Data Flow

1. Data Ingestion
   ```python
   from nova.ephemeral import EphemeralManager
   
   # Initialize manager
   manager = EphemeralManager(
       embedding_dim=384,
       default_ttl=300,  # 5 minutes
       cleanup_interval=60  # Check expiry every minute
   )
   
   # Add data with embedding
   data_id = manager.add_data(
       content="Some temporary content",
       metadata={"source": "chat"},
       embedding=vector,
       ttl=600  # Override default TTL
   )
   ```

2. Data Retrieval
   ```python
   # Get data by ID
   data = manager.get_data(data_id)
   if data:
       print(f"Content: {data.content}")
       print(f"Expires in: {data.expiration - time.time()} seconds")
   
   # Search similar vectors
   results = manager.search(query_vector, k=5)
   for result in results:
       print(f"Score: {result.score}")
       print(f"Content: {result.chunk.content}")
   ```

3. TTL Extension
   ```python
   # Extend TTL for important data
   if manager.extend_ttl(data_id, extension=300):
       print("TTL extended by 5 minutes")
   ```

4. Automatic Cleanup
   - Cleanup runs automatically based on cleanup_interval
   - Expired data is removed from both storage and index
   - Index is optimized after cleanup
   - Memory usage is monitored and alerts are triggered if needed

## Common Use Cases

1. Chat History
   ```python
   # Store chat messages with 1-hour TTL
   message_id = manager.add_data(
       content=message_text,
       metadata={
           "sender": "user",
           "timestamp": time.time()
       },
       embedding=message_vector,
       ttl=3600
   )
   ```

2. Session Context
   ```python
   # Store session-specific data
   session_id = manager.add_data(
       content=json.dumps(session_data),
       metadata={
           "session_id": "abc123",
           "user_id": "user456"
       },
       ttl=1800  # 30 minutes
   )
   ```

3. Temporary Search Results
   ```python
   # Store search results temporarily
   for result in search_results:
       manager.add_data(
           content=result.text,
           metadata={
               "query": original_query,
               "rank": result.rank
           },
           embedding=result.embedding,
           ttl=300  # 5 minutes
       )
   ```

## Edge Cases and Limitations

1. Data Consistency
   - Data might expire between get_data() and actual use
   - Always check for None return values
   - Use try/except when accessing data properties

2. Vector Search
   - Search results might include recently expired data
   - Results are filtered post-search
   - k might return fewer results than requested

3. Memory Management
   - Large number of vectors can impact memory
   - Cleanup rebuilds index which can be CPU intensive
   - GPU memory needs to be managed carefully

4. Concurrent Access
   - Thread-safe for reads
   - Writes and cleanup may block temporarily
   - Extend TTL may fail if data expires during call

## Best Practices

1. TTL Management
   ```python
   # Use shorter TTL for large data
   if len(content) > 10000:
       ttl = 300  # 5 minutes
   else:
       ttl = 3600  # 1 hour
   ```

2. Memory Optimization
   ```python
   # Use IVF index for large datasets
   manager = EphemeralManager(
       embedding_dim=384,
       n_lists=100,  # IVF lists
       n_probe=25    # Search depth
   )
   ```

3. Error Handling
   ```python
   try:
       data = manager.get_data(data_id)
       if data is None:
           # Handle expired data
           pass
       # Use data
   except Exception as e:
       logger.error(f"Error accessing ephemeral data: {e}")
   ```

4. Monitoring
   ```python
   # Initialize with monitoring
   manager = EphemeralManager(
       alert_manager=alert_manager,
       memory_monitor=memory_monitor
   )
   ```

## Performance Considerations

1. Cleanup Impact
   - Cleanup rebuilds index
   - More frequent cleanup = smaller index rebuilds
   - Less frequent = larger rebuilds but less CPU usage

2. GPU Acceleration
   - Beneficial for >100K vectors
   - Requires GPU memory management
   - Falls back to CPU gracefully

3. Memory Usage
   - Each vector uses embedding_dim * 4 bytes
   - Metadata and content stored separately
   - Monitor memory_gauge metric

4. Search Performance
   - O(n) for flat index
   - O(log n) for IVF index
   - GPU provides 3-10x speedup

## Monitoring and Metrics

1. Available Metrics
   - VECTOR_SEARCH_LATENCY
   - VECTOR_STORE_MEMORY
   - VECTOR_STORE_SIZE
   - VECTOR_STORE_VECTORS

2. Alerting
   - Memory pressure alerts
   - Large store size alerts
   - Cleanup performance alerts

3. Logging
   - Initialization status
   - Cleanup operations
   - Error conditions
   - Performance issues 